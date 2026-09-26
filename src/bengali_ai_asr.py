import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import soundfile as sf
import numpy as np

from src.models import WordTimestamp
from src.config import default_config
from src.audio import extract_audio, get_audio_info

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm", ".wmv",
    ".m4v", ".3gp", ".ts", ".mts", ".mpg", ".mpeg", ".m2ts", ".vob", ".ogv"
}

class BengaliAIASREngine:
    """
    Client for Regional Bengali Whisper ASR on Hugging Face Spaces.
    Supports:
    1. Primary: ybtheflash/regional_bengali-asr_tugstugi_whisper-medium (endpoint: /transcribe_mic, with /transcribe_file fallback)
    2. Fallback: bengaliAI/regional_bengali-asr_tugstugi_whisper-medium (endpoint: /transcribe)

    CRITICAL REQUIREMENT:
    These Hugging Face Spaces do NOT accept video files directly; they only support audio files (.wav).
    If a video file or container is supplied, it is automatically extracted to a 16kHz mono WAV first.
    """

    MODAL_XLSR_URL = os.getenv("MODAL_XLSR_URL", "https://ybtheflash--bengali-asr-asr-web.modal.run")
    MODAL_WHISPER_URL = os.getenv("MODAL_WHISPER_URL", "https://ybtheflash--whisper-bengali-whisperasr-web.modal.run")
    SPACE_YBTHEFLASH_WHISPER = "ybtheflash/regional_bengali-asr_tugstugi_whisper-medium"
    SPACE_BENGALIAI_WHISPER = "bengaliAI/regional_bengali-asr_tugstugi_whisper-medium"
    SPACE_YBTHEFLASH_XLSR = "ybtheflash/bengali-asr"

    def __init__(
        self,
        primary_whisper_space: str = SPACE_YBTHEFLASH_WHISPER,
        fallback_whisper_space: str = SPACE_BENGALIAI_WHISPER,
        xlsr_space: str = SPACE_YBTHEFLASH_XLSR,
        modal_xlsr_url: str = MODAL_XLSR_URL,
        modal_whisper_url: str = MODAL_WHISPER_URL,
        hf_token: Optional[str] = None,
        timeout: float = 180.0
    ):
        self.primary_whisper_space = primary_whisper_space
        self.fallback_whisper_space = fallback_whisper_space
        self.xlsr_space = xlsr_space
        self.modal_xlsr_url = modal_xlsr_url.rstrip("/")
        self.modal_whisper_url = modal_whisper_url.rstrip("/")
        self.hf_token = (hf_token or default_config.hf_token or "").strip() or None
        self.timeout = timeout
        self._clients: Dict[str, Any] = {}

    def _get_client(self, space_id: str):
        if space_id not in self._clients:
            try:
                from gradio_client import Client
                logger.info(f"Initializing Gradio Client for space '{space_id}' (token={'configured' if self.hf_token else 'none'})")
                if self.hf_token:
                    self._clients[space_id] = Client(space_id, token=self.hf_token)
                else:
                    self._clients[space_id] = Client(space_id)
            except Exception as e:
                logger.error(f"Failed to initialize Gradio Client for '{space_id}': {e}")
                raise
        return self._clients[space_id]

    def _ensure_audio_file(self, file_path: str) -> Tuple[str, bool]:
        """
        Ensures the input file is strictly a valid audio file (.wav).
        If the input is a video file or unreadable audio container, it automatically
        extracts a 16kHz mono WAV audio file using ffmpeg before sending to Gradio.

        Returns:
            Tuple[audio_path_to_use, is_temp_file]
        """
        p = Path(file_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        ext = p.suffix.lower()
        is_video = ext in VIDEO_EXTENSIONS

        # Check if file can be opened directly with soundfile
        needs_extraction = is_video
        if not is_video:
            try:
                with sf.SoundFile(str(p)) as sf_file:
                    if sf_file.samplerate <= 0:
                        needs_extraction = True
            except Exception:
                needs_extraction = True

        if needs_extraction:
            logger.info(f"[BengaliAI ASR] Input '{p.name}' is video/non-standard format. Extracting 16kHz mono WAV audio before calling Gradio ASR API.")
            temp_dir = default_config.temp_dir
            temp_dir.mkdir(parents=True, exist_ok=True)
            extracted_wav = temp_dir / f"extracted_asr_{p.stem}_{int(time.time())}.wav"
            extract_audio(str(p), str(extracted_wav), sample_rate=16000, channels=1)
            return str(extracted_wav), True

        return str(p), False

    def transcribe_xlsr(
        self,
        audio_path: str,
        model_key: str = "xlsr",
        use_lm: bool = False
    ) -> Tuple[List[WordTimestamp], List[Dict[str, Any]]]:
        """
        Transcribes audio using Modal primary (https://ybtheflash--bengali-asr-asr-web.modal.run)
        with fallback to Hugging Face Space (ybtheflash/bengali-asr).
        """
        clean_audio_path, is_temp = self._ensure_audio_file(audio_path)
        try:
            audio_p = Path(clean_audio_path).resolve()
            with sf.SoundFile(str(audio_p)) as f:
                duration = len(f) / float(f.samplerate)

            raw_text = None
            t0 = time.time()

            # 1. Primary: Modal Fast Cloud Endpoint
            if self.modal_xlsr_url:
                try:
                    logger.info(f"Submitting pure audio ({duration:.2f}s) to Modal Primary Bengali XLS-R: {self.modal_xlsr_url}/transcribe")
                    import requests
                    with open(str(audio_p), "rb") as f_audio:
                        r = requests.post(
                            f"{self.modal_xlsr_url}/transcribe",
                            files={"file": (audio_p.name, f_audio, "audio/wav")},
                            data={"model_key": model_key},
                            timeout=min(self.timeout, 90.0)
                        )
                    if r.status_code == 200:
                        data = r.json()
                        raw_text = str(data.get("text", "")).strip()
                        elapsed = time.time() - t0
                        logger.info(f"Modal XLS-R completed in {elapsed:.2f}s. Result: '{raw_text[:60]}...'")
                    else:
                        logger.warning(f"Modal XLS-R returned HTTP {r.status_code}: {r.text[:120]}")
                except Exception as e_modal:
                    logger.warning(f"Modal Primary XLS-R call failed ({e_modal}). Falling back to Hugging Face Space '{self.xlsr_space}'...")

            # 2. Fallback: Hugging Face Gradio Space
            if raw_text is None:
                from gradio_client import handle_file
                logger.info(f"Submitting pure audio ({duration:.2f}s) to Hugging Face fallback: {self.xlsr_space}")
                client = self._get_client(self.xlsr_space)
                t0_hf = time.time()
                result = client.predict(
                    audio_path=handle_file(str(audio_p)),
                    model_key=model_key,
                    use_lm=use_lm,
                    api_name="/transcribe"
                )
                elapsed_hf = time.time() - t0_hf
                if isinstance(result, (list, tuple)):
                    raw_text = str(result[0]).strip() if result else ""
                else:
                    raw_text = str(result).strip() if result else ""
                logger.info(f"Hugging Face Space '{self.xlsr_space}' completed in {elapsed_hf:.2f}s. Result: '{raw_text[:60]}...'")

            if not raw_text:
                logger.warning("Bengali XLS-R ASR returned empty transcription.")
                return [], []

            words = self._words_from_text(raw_text, 0.0, duration)
            segments = [{
                "start": 0.0,
                "end": round(duration, 3),
                "text": raw_text,
                "avg_logprob": 0.95,
                "no_speech_prob": 0.05
            }]
            return words, segments
        finally:
            if is_temp:
                try:
                    Path(clean_audio_path).unlink(missing_ok=True)
                except Exception:
                    pass

    def transcribe_whisper(
        self,
        audio_path: str,
        timeout: Optional[float] = None,
        preferred_space: Optional[str] = None
    ) -> Tuple[List[WordTimestamp], List[Dict[str, Any]]]:
        """
        Transcribes audio using Modal primary (https://ybtheflash--whisper-bengali-whisperasr-web.modal.run)
        with fallback to Hugging Face Spaces (ybtheflash / bengaliAI).
        """
        clean_audio_path, is_temp = self._ensure_audio_file(audio_path)
        try:
            audio_p = Path(clean_audio_path).resolve()
            with sf.SoundFile(str(audio_p)) as f:
                duration = len(f) / float(f.samplerate)

            raw_text = None
            t0 = time.time()

            # 1. Primary: Modal Regional Whisper Cloud Endpoint
            if self.modal_whisper_url:
                try:
                    logger.info(f"Submitting pure audio ({duration:.2f}s) to Modal Primary Regional Whisper: {self.modal_whisper_url}/transcribe")
                    import requests
                    with open(str(audio_p), "rb") as f_audio:
                        r = requests.post(
                            f"{self.modal_whisper_url}/transcribe",
                            files={"file": (audio_p.name, f_audio, "audio/wav")},
                            timeout=min(self.timeout, 120.0)
                        )
                    if r.status_code == 200:
                        data = r.json()
                        raw_text = str(data.get("text", "")).strip()
                        elapsed = time.time() - t0
                        logger.info(f"Modal Regional Whisper completed in {elapsed:.2f}s. Result: '{raw_text[:60]}...'")
                    else:
                        logger.warning(f"Modal Regional Whisper returned HTTP {r.status_code}: {r.text[:120]}")
                except Exception as e_modal:
                    logger.warning(f"Modal Primary Regional Whisper failed ({e_modal}). Falling back to Hugging Face Spaces...")

            # 2. Fallback: Hugging Face Gradio Spaces (ybtheflash -> bengaliAI)
            if raw_text is None:
                from gradio_client import handle_file
                logger.info(f"Submitting pure audio ({duration:.2f}s) to Hugging Face fallback spaces...")
                spaces_to_try = []
                if preferred_space:
                    spaces_to_try.append(preferred_space)
                if self.primary_whisper_space not in spaces_to_try:
                    spaces_to_try.append(self.primary_whisper_space)
                if self.fallback_whisper_space not in spaces_to_try:
                    spaces_to_try.append(self.fallback_whisper_space)

                last_error = None
                for space_id in spaces_to_try:
                    try:
                        client = self._get_client(space_id)
                        t0_hf = time.time()

                        if "ybtheflash" in space_id.lower():
                            try:
                                logger.info(f"Submitting to {space_id} (api_name='/transcribe_mic')...")
                                result = client.predict(
                                    inputs=handle_file(str(audio_p)),
                                    api_name="/transcribe_mic"
                                )
                            except Exception as e_mic:
                                logger.warning(f"{space_id} /transcribe_mic failed ({e_mic}). Trying /transcribe_file...")
                                result = client.predict(
                                    inputs=handle_file(str(audio_p)),
                                    api_name="/transcribe_file"
                                )
                        else:
                            logger.info(f"Submitting to {space_id} (api_name='/transcribe')...")
                            result = client.predict(
                                inputs=handle_file(str(audio_p)),
                                api_name="/transcribe"
                            )

                        elapsed_hf = time.time() - t0_hf
                        raw_text = str(result).strip() if result else ""
                        logger.info(f"Hugging Face space '{space_id}' completed in {elapsed_hf:.2f}s. Result: '{raw_text[:60]}...'")
                        break
                    except Exception as e:
                        last_error = e
                        logger.warning(f"ASR call to space '{space_id}' failed: {e}. Trying next available space...")

                if raw_text is None:
                    raise RuntimeError(f"All Bengali AI Modal & Hugging Face endpoints failed. Last error: {last_error}")

            if not raw_text:
                logger.warning("Bengali ASR returned empty transcription.")
                return [], []

            words = self._words_from_text(raw_text, 0.0, duration)
            segments = [{
                "start": 0.0,
                "end": round(duration, 3),
                "text": raw_text,
                "avg_logprob": 0.95,
                "no_speech_prob": 0.05
            }]

            return words, segments
        finally:
            if is_temp:
                try:
                    Path(clean_audio_path).unlink(missing_ok=True)
                except Exception:
                    pass

    def transcribe(
        self,
        audio_path: str,
        model_type: str = "whisper",
        timeout: Optional[float] = None
    ) -> Tuple[List[WordTimestamp], List[Dict[str, Any]]]:
        """
        Unified transcribe dispatcher.
        If model_type is 'xlsr', uses ybtheflash/bengali-asr.
        Otherwise uses Regional Whisper Medium.
        """
        if model_type in ("xlsr", "bengali_xlsr", "bengali-asr"):
            return self.transcribe_xlsr(audio_path=audio_path)
        return self.transcribe_whisper(audio_path=audio_path, timeout=timeout)

    def _words_from_text(self, text: str, start_sec: float, end_sec: float) -> List[WordTimestamp]:
        tokens = text.strip().split()
        if not tokens:
            return []

        total_duration = max(0.2, end_sec - start_sec)
        total_chars = sum(len(t) for t in tokens)
        if total_chars == 0:
            total_chars = len(tokens)

        words: List[WordTimestamp] = []
        current_time = start_sec

        for tok in tokens:
            word_fraction = len(tok) / float(total_chars)
            word_duration = max(0.08, word_fraction * total_duration)
            w_start = round(current_time, 3)
            w_end = round(min(end_sec, current_time + word_duration), 3)

            words.append(
                WordTimestamp(
                    word=tok,
                    start=w_start,
                    end=w_end,
                    confidence=0.95
                )
            )
            current_time = w_end

        return words

