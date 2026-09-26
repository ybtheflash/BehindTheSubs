import os
import time
import base64
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import httpx
import soundfile as sf
import numpy as np

from src.models import WordTimestamp
from src.config import default_config

logger = logging.getLogger(__name__)

class MiMoASREngine:
    """
    Client for Xiaomi MiMo ASR 2.5 (mimo-v2.5-asr).
    API Docs: https://mimo.mi.com/docs/en-US/quick-start/usage-guide/audio/Speech-Recognition

    Features:
    - Base64 audio encoding
    - Multi-key pool with automatic rotation and failover
    - Audio chunking for files exceeding MiMo 10MB limit
    - Bengali code-switched transcription support
    """

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        base_url: str = default_config.mimo_base_url,
        model: str = default_config.mimo_model,
        language: str = "bn"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.language = language
        self.api_keys = [k for k in (api_keys or default_config.get_mimo_keys()) if k.strip()]
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
                f"Rotating MiMo API key from index {prev} to index {self.current_key_idx} (pool size: {len(self.api_keys)})"
            )

    def transcribe(
        self,
        audio_path: str,
        specific_key: Optional[str] = None,
        language: Optional[str] = None
    ) -> Tuple[List[WordTimestamp], List[Dict[str, Any]]]:
        """
        Transcribes the given 16kHz mono audio file using Xiaomi MiMo ASR 2.5.
        Handles audio chunking if duration > 180s (MiMo 10MB base64 limit).
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
                "No Xiaomi MiMo API key provided. Please configure MIMO_API_KEY in .env or pass a key in the settings panel."
            )

        # Inspect audio duration & size
        with sf.SoundFile(str(target_path)) as f:
            sr = f.samplerate
            total_frames = len(f)
            duration = total_frames / float(sr)

        logger.info(f"Preparing MiMo ASR 2.5 transcription: {audio_path} ({duration:.2f}s)")

        # MiMo 10MB base64 limit ~= ~200 seconds of 16kHz mono audio
        chunk_max_sec = 180.0
        if duration <= chunk_max_sec:
            # Process single chunk
            text, raw_meta = self._call_mimo_api_with_retry(str(target_path), key_pool, language)
            words = self._words_from_text(text, 0.0, duration)
            return words, [{
                "start": 0.0,
                "end": round(duration, 3),
                "text": text,
                "avg_logprob": 0.95,
                "no_speech_prob": 0.05
            }]

        # For long audio, chunk into <=180s pieces and merge
        logger.info(f"Audio duration {duration:.1f}s exceeds MiMo chunk limit. Chunking into {chunk_max_sec}s slices.")
        audio_data, _ = sf.read(str(target_path), dtype="float32")
        all_words: List[WordTimestamp] = []
        all_segments: List[Dict[str, Any]] = []

        chunk_samples = int(chunk_max_sec * sr)
        temp_dir = default_config.temp_dir / "mimo_chunks"
        temp_dir.mkdir(parents=True, exist_ok=True)

        for chunk_idx, start_sample in enumerate(range(0, total_frames, chunk_samples)):
            end_sample = min(total_frames, start_sample + chunk_samples)
            chunk_slice = audio_data[start_sample:end_sample]
            start_sec = start_sample / float(sr)
            end_sec = end_sample / float(sr)

            chunk_file = temp_dir / f"chunk_{chunk_idx}_{target_path.stem}.wav"
            sf.write(str(chunk_file), chunk_slice, sr)

            logger.info(f"Sending MiMo ASR chunk {chunk_idx + 1}: {start_sec:.1f}s - {end_sec:.1f}s")
            chunk_text, _ = self._call_mimo_api_with_retry(str(chunk_file), key_pool, language)

            chunk_words = self._words_from_text(chunk_text, start_sec, end_sec)
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

    def _call_mimo_api_with_retry(
        self,
        audio_file: str,
        key_pool: List[str],
        language: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Calls MiMo chat/completions endpoint with base64 audio.
        Automatically retries across keys in the pool if one fails.
        """
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        lang = (language or self.language or "bn").lower()
        # Xiaomi MiMo ASR 2.5 API only accepts 'zh', 'en', 'auto' in asr_options.language
        # Passing 'bn' causes HTTP 400 ('Param Incorrect: asr_options.language must be one of: zh, en, auto').
        # We pass 'auto' (or specific 'zh'/'en' if requested) and guide the model strictly to Bengali dialogue
        # via the system message prompt.
        mimo_lang = lang if lang in ("zh", "en") else "auto"

        system_instruction = (
            "You are a professional Bengali speech-to-text transcriber. "
            "The audio is strictly spoken Bengali dialogue (বাংলা), with occasional code-switched English words or Hindi lines. "
            "Transcribe the spoken audio verbatim in standard Bengali script (বাংলা লিপি). "
            "Accurately preserve code-switched English terms and Hindi phrases exactly as spoken."
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:audio/wav;base64,{audio_base64}"
                            }
                        }
                    ]
                }
            ],
            "asr_options": {
                "language": mimo_lang
            }
        }

        url = f"{self.base_url}/chat/completions"
        last_error = None

        # Try keys in pool
        for key_idx, key in enumerate(key_pool):
            headers = {
                "api-key": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            logger.info(f"Calling MiMo ASR 2.5 API with key index {key_idx + 1}/{len(key_pool)} ({key[:4]}...)")

            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "").strip()
                        logger.info(f"MiMo ASR 2.5 response received: '{content[:60]}...'")
                        return content, data
                    return "", data

                logger.warning(
                    f"MiMo API key #{key_idx + 1} returned HTTP {response.status_code}: {response.text[:200]}"
                )
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"

            except Exception as e:
                logger.warning(f"MiMo API request failed with key #{key_idx + 1}: {e}")
                last_error = str(e)

        raise RuntimeError(
            f"All configured Xiaomi MiMo API keys failed. Last error: {last_error}"
        )

    def _words_from_text(self, text: str, start_sec: float, end_sec: float) -> List[WordTimestamp]:
        """
        Splits recognized text into sequential words with interpolated timestamps.
        """
        tokens = text.strip().split()
        if not tokens:
            return []

        duration = max(0.2, end_sec - start_sec)
        dt = duration / len(tokens)
        words: List[WordTimestamp] = []

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
