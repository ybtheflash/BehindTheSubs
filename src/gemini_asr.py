import os
import time
import json
import base64
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import httpx
import soundfile as sf

from src.models import WordTimestamp
from src.config import default_config

logger = logging.getLogger(__name__)

class GeminiASREngine:
    """
    Client for Google Gemini Audio ASR using gemini-flash-latest.
    Uses Google Generative Language v1beta REST API with Base64 audio.

    Features:
    - Zero extra library dependencies (pure httpx + soundfile)
    - Multi-key pool with automatic rotation and failover
    - Audio chunking for long files (> 180s)
    - Bengali transcription with code-switching preservation
    - Automatic fallback and timestamp interpolation
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        model: Optional[str] = None,
        language: str = "bn"
    ):
        self.model = model or default_config.gemini_model or "gemini-flash-latest"
        self.language = language
        self.api_keys = [k for k in (api_keys or default_config.get_gemini_keys()) if k.strip()]
        self.current_key_idx = 0

    def add_key(self, key: str):
        if key and key.strip() and key.strip() not in self.api_keys:
            self.api_keys.append(key.strip())

    def get_current_key(self) -> Optional[str]:
        if not self.api_keys:
            return None
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def rotate_key(self):
        if len(self.api_keys) > 1:
            prev = self.current_key_idx
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            logger.warning(
                f"Rotating Gemini API key from index {prev} to index {self.current_key_idx} (pool size: {len(self.api_keys)})"
            )

    def transcribe(
        self,
        audio_path: str,
        specific_key: Optional[str] = None,
        language: Optional[str] = None
    ) -> Tuple[List[WordTimestamp], List[Dict[str, Any]]]:
        """
        Transcribes the given 16kHz mono audio file using Google Gemini Flash.
        Handles audio chunking if duration > 180s.
        Returns:
            - List of WordTimestamp objects
            - List of raw segment metadata
        """
        target_path = Path(audio_path)
        if not target_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        key_pool = [specific_key.strip()] if (specific_key and specific_key.strip()) else list(self.api_keys)
        if not key_pool:
            raise ValueError(
                "No Google Gemini API key provided. Please configure GEMINI_API_KEY in .env or pass a key in the settings panel."
            )

        # Inspect audio duration & size
        with sf.SoundFile(str(target_path)) as f:
            sr = f.samplerate
            total_frames = len(f)
            duration = total_frames / float(sr)

        logger.info(f"Preparing Gemini ({self.model}) ASR transcription: {audio_path} ({duration:.2f}s)")

        chunk_max_sec = 180.0
        if duration <= chunk_max_sec:
            # Process single chunk
            text, segments_raw = self._call_gemini_api_with_retry(str(target_path), key_pool, 0.0, duration)
            words = self._words_from_segments_or_text(text, segments_raw, 0.0, duration)
            return words, [{
                "start": 0.0,
                "end": round(duration, 3),
                "text": text,
                "avg_logprob": 0.95,
                "no_speech_prob": 0.05
            }]

        # Long audio chunking
        logger.info(f"Audio duration {duration:.1f}s exceeds {chunk_max_sec}s. Chunking into slices.")
        audio_data, _ = sf.read(str(target_path), dtype="float32")
        all_words: List[WordTimestamp] = []
        all_segments: List[Dict[str, Any]] = []

        chunk_samples = int(chunk_max_sec * sr)
        temp_dir = default_config.temp_dir / "gemini_chunks"
        temp_dir.mkdir(parents=True, exist_ok=True)

        for chunk_idx, start_sample in enumerate(range(0, total_frames, chunk_samples)):
            end_sample = min(total_frames, start_sample + chunk_samples)
            chunk_slice = audio_data[start_sample:end_sample]
            start_sec = start_sample / float(sr)
            end_sec = end_sample / float(sr)

            chunk_file = temp_dir / f"chunk_{chunk_idx}_{target_path.stem}.wav"
            sf.write(str(chunk_file), chunk_slice, sr)

            logger.info(f"Sending Gemini ASR chunk {chunk_idx + 1}: {start_sec:.1f}s - {end_sec:.1f}s")
            chunk_text, chunk_segs = self._call_gemini_api_with_retry(str(chunk_file), key_pool, start_sec, end_sec)

            chunk_words = self._words_from_segments_or_text(chunk_text, chunk_segs, start_sec, end_sec)
            all_words.extend(chunk_words)
            all_segments.append({
                "start": round(start_sec, 3),
                "end": round(end_sec, 3),
                "text": chunk_text,
                "avg_logprob": 0.95,
                "no_speech_prob": 0.05
            })

            try:
                chunk_file.unlink(missing_ok=True)
            except Exception:
                pass

        return all_words, all_segments

    def _call_gemini_api_with_retry(
        self,
        audio_file: str,
        key_pool: List[str],
        offset_sec: float,
        end_sec: float
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Sends base64 audio to Google Gemini generateContent REST API.
        Tries keys sequentially in case of rate-limiting, quota errors, or auth issues.
        """
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        prompt_text = (
            "You are a professional Bengali audio transcriber and subtitler.\n"
            "The primary language of this audio is strictly Bengali (ISO 639-1: 'bn').\n"
            "Transcribe all spoken Bengali dialogue verbatim into standard Bengali script (বাংলা লিপি).\n"
            "If speakers code-switch or use English words (e.g., 'office', 'meeting', 'phone', 'police') or Hindi phrases, "
            "transcribe them faithfully as spoken without dropping them or translating them.\n"
            "Do NOT output English-only translations in place of Bengali transcription.\n"
            "Do NOT add commentary, notes, or explanations.\n"
            "Format your response strictly as a valid JSON object matching this structure:\n"
            "{\n"
            "  \"transcript\": \"complete text here\",\n"
            "  \"segments\": [\n"
            "    {\"start\": 0.0, \"end\": 2.5, \"text\": \"spoken phrase in Bengali script\"}\n"
            "  ]\n"
            "}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "audio/wav",
                                "data": audio_b64
                            }
                        },
                        {
                            "text": prompt_text
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        last_error = None
        # Candidate models to try if the primary encounters 503 high demand or 404
        candidate_models = [self.model]
        for fallback_m in ("gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"):
            if fallback_m not in candidate_models:
                candidate_models.append(fallback_m)

        for current_model in candidate_models:
            for key_idx, key in enumerate(key_pool):
                masked_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "Key"
                url = f"{self.BASE_URL}/{current_model}:generateContent?key={key}"
                logger.info(f"Calling Gemini ({current_model}) with key #{key_idx + 1}/{len(key_pool)} ({masked_key})")

                # Try up to 2 times for temporary 503 demand spikes
                for attempt in range(2):
                    try:
                        with httpx.Client(timeout=60.0) as client:
                            response = client.post(url, json=payload, headers={"Content-Type": "application/json"})

                        if response.status_code == 200:
                            data = response.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    raw_text = parts[0].get("text", "").strip()
                                    logger.info(f"Gemini ASR ({current_model}) returned text: '{raw_text[:80]}...'")
                                    parsed_text, segments = self._parse_gemini_json(raw_text, offset_sec, end_sec)
                                    return parsed_text, segments
                            return "", []

                        err_snippet = response.text[:200]
                        logger.warning(
                            f"Gemini API ({current_model}) key #{key_idx + 1} ({masked_key}) returned HTTP {response.status_code}: {err_snippet}"
                        )
                        last_error = f"HTTP {response.status_code} ({current_model}): {err_snippet}"

                        # If 503 (high demand) or 429, wait 1.2s and retry once, or continue to next model
                        if response.status_code in (503, 429) and attempt == 0:
                            time.sleep(1.2)
                            continue
                        break

                    except Exception as e:
                        logger.warning(f"Gemini API request failed ({current_model}) with key #{key_idx + 1}: {e}")
                        last_error = str(e)
                        break

        raise RuntimeError(
            f"All configured Google Gemini API keys and models failed. Last error: {last_error}"
        )

    def _parse_gemini_json(
        self,
        raw_output: str,
        chunk_offset: float,
        chunk_end: float
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parses JSON output from Gemini response, with fallback to raw string.
        """
        clean = raw_output.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            parsed = json.loads(clean)
            if isinstance(parsed, dict):
                full_text = parsed.get("transcript") or parsed.get("text") or ""
                raw_segs = parsed.get("segments", [])
                segments: List[Dict[str, Any]] = []
                for s in raw_segs:
                    if isinstance(s, dict) and "text" in s:
                        # Add chunk_offset to segment timestamps
                        s_start = round(float(s.get("start", 0.0)) + chunk_offset, 3)
                        s_end = round(float(s.get("end", chunk_end - chunk_offset)) + chunk_offset, 3)
                        segments.append({
                            "start": s_start,
                            "end": s_end,
                            "text": str(s["text"]).strip()
                        })
                return full_text, segments
        except Exception:
            pass

        # If not structured JSON, treat entire output as transcript
        return clean, []

    def _words_from_segments_or_text(
        self,
        text: str,
        segments: List[Dict[str, Any]],
        start_sec: float,
        end_sec: float
    ) -> List[WordTimestamp]:
        """
        Extracts sequential WordTimestamp objects using segment timestamps if available,
        otherwise interpolates across (start_sec, end_sec).
        """
        words: List[WordTimestamp] = []

        if segments:
            for seg in segments:
                seg_text = seg.get("text", "").strip()
                seg_start = seg.get("start", start_sec)
                seg_end = seg.get("end", end_sec)
                tokens = seg_text.split()
                if not tokens:
                    continue
                dur = max(0.1, seg_end - seg_start)
                dt = dur / len(tokens)
                for i, tok in enumerate(tokens):
                    w_start = round(seg_start + i * dt, 3)
                    w_end = round(seg_start + (i + 1) * dt, 3)
                    words.append(
                        WordTimestamp(
                            word=tok,
                            start=w_start,
                            end=w_end,
                            confidence=0.94
                        )
                    )
            if words:
                return words

        # Fallback to interpolation across entire chunk
        tokens = text.strip().split()
        if not tokens:
            return []

        duration = max(0.2, end_sec - start_sec)
        dt = duration / len(tokens)
        for i, tok in enumerate(tokens):
            w_start = round(start_sec + i * dt, 3)
            w_end = round(start_sec + (i + 1) * dt, 3)
            words.append(
                WordTimestamp(
                    word=tok,
                    start=w_start,
                    end=w_end,
                    confidence=0.92
                )
            )

        return words
