import logging
from typing import List, Dict, Any, Tuple, Optional
from faster_whisper import WhisperModel
from src.models import WordTimestamp
from src.config import default_config
from src.mimo_asr import MiMoASREngine
from src.gemini_asr import GeminiASREngine
from src.whisper_cpp_engine import WhisperCppEngine
from src.bengali_ai_asr import BengaliAIASREngine

logger = logging.getLogger(__name__)

class UnifiedASREngine:
    """
    Unified Speech Recognition Engine supporting:
    1. BengaliAI Regional Whisper Medium (Hugging Face Spaces: bengaliAI/regional_bengali-asr_tugstugi_whisper-medium)
    2. Google Gemini Flash (Cloud Multimodal API: gemini-flash-latest)
    3. whisper.cpp (whisper.cpp-1.9.4 C++ AVX2 Native Inference)
    4. Xiaomi MiMo ASR 2.5 (Cloud High Performance API: mimo-v2.5-asr)

    Supports hot-switching between providers and API keys from the UI panel.
    """

    def __init__(
        self,
        default_provider: str = default_config.asr_provider,
        model_size: str = default_config.asr_model,
        device: str = default_config.asr_device,
        compute_type: str = default_config.asr_compute_type,
        language: str = default_config.asr_language
    ):
        self.default_provider = default_provider
        self.model_size = model_size
        self.device = device if device in ("cpu", "cuda") else "cpu"
        self.compute_type = compute_type
        self.language = language
        self.whisper_model: Optional[WhisperModel] = None
        self.bengali_ai_engine = BengaliAIASREngine()
        self.whisper_cpp_engine = WhisperCppEngine(
            whisper_cpp_dir=default_config.whisper_cpp_dir,
            model=default_config.whisper_cpp_model,
            threads=default_config.whisper_cpp_threads,
            language=language
        )
        self.mimo_engine = MiMoASREngine(
            base_url=default_config.mimo_base_url,
            model=default_config.mimo_model,
            language=language
        )
        self.gemini_engine = GeminiASREngine(
            model=default_config.gemini_model,
            language=language
        )

    def load_whisper(self):
        if self.whisper_model is None:
            logger.info(f"Loading faster-whisper model '{self.model_size}' on device '{self.device}' with '{self.compute_type}'")
            try:
                self.whisper_model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
            except Exception as e:
                logger.warning(f"Failed to load with compute_type '{self.compute_type}', falling back to 'float32': {e}")
                self.whisper_model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="float32"
                )

    def transcribe(
        self,
        audio_path: str,
        provider: Optional[str] = None,
        mimo_key: Optional[str] = None,
        gemini_key: Optional[str] = None,
        beam_size: int = 5,
        word_timestamps: bool = True
    ) -> Tuple[List[WordTimestamp], List[Dict[str, Any]], str]:
        """
        Transcribes audio using Xiaomi MiMo ASR 2.5, Google Gemini Flash, or Faster-Whisper.
        Returns:
            - List[WordTimestamp]
            - List[Dict[str, Any]] (segments)
            - str: the provider actually used ('mimo', 'gemini', or 'faster-whisper')
        """
        active_provider = (provider or self.default_provider or "bengali_ai").lower()

        # Try Bengali XLS-R ASR (ybtheflash/bengali-asr)
        if active_provider in ("bengali_xlsr", "xlsr", "bengali-asr", "ybtheflash-bengali-asr"):
            logger.info("Using Bengali XLS-R ASR provider (ybtheflash/bengali-asr).")
            try:
                words, segments = self.bengali_ai_engine.transcribe_xlsr(audio_path=audio_path)
                logger.info(f"Bengali XLS-R ASR transcribed {len(words)} words across {len(segments)} segments.")
                return words, segments, "bengali_xlsr"
            except Exception as e:
                logger.warning(f"Bengali XLS-R ASR failed: {e}. Gracefully falling back to whisper.cpp.")

        # Try Bengali Regional Whisper Medium (ybtheflash / bengaliAI)
        elif active_provider in ("bengali_whisper", "bengali_ai", "bengali-ai", "regional_bengali", "bengaliai", "ybtheflash", "tugstugi"):
            logger.info("Using Bengali Regional Whisper Medium ASR provider (gradio_client).")
            try:
                words, segments = self.bengali_ai_engine.transcribe_whisper(audio_path=audio_path)
                logger.info(f"Bengali Regional Whisper Medium transcribed {len(words)} words across {len(segments)} segments.")
                return words, segments, "bengali_whisper"
            except Exception as e:
                logger.warning(f"Bengali Regional Whisper Medium ASR failed: {e}. Gracefully falling back to whisper.cpp.")

        # Try Google Gemini Flash if requested
        elif active_provider in ("gemini", "gemini-flash-latest", "gemini-flash", "google-gemini"):
            logger.info(f"Using Google Gemini Flash ({self.gemini_engine.model}) ASR provider.")
            try:
                words, segments = self.gemini_engine.transcribe(
                    audio_path=audio_path,
                    specific_key=gemini_key or mimo_key,
                    language=self.language
                )
                logger.info(f"Gemini Flash transcribed {len(words)} words across {len(segments)} segments.")
                return words, segments, "gemini"
            except Exception as e:
                logger.warning(f"Google Gemini Flash ASR failed: {e}. Gracefully falling back to whisper.cpp.")

        # Try MiMo ASR 2.5 if requested
        elif active_provider == "mimo":
            logger.info("Using Xiaomi MiMo ASR 2.5 provider.")
            try:
                words, segments = self.mimo_engine.transcribe(
                    audio_path=audio_path,
                    specific_key=mimo_key,
                    language=self.language
                )
                logger.info(f"MiMo ASR 2.5 transcribed {len(words)} words across {len(segments)} segments.")
                return words, segments, "mimo"
            except Exception as e:
                logger.warning(f"MiMo ASR 2.5 failed: {e}. Gracefully falling back to whisper.cpp.")

        # Primary Local Engine: whisper.cpp-1.9.4 Native C++ Inference
        logger.info(f"Using whisper.cpp-1.9.4 ASR engine (model: {self.whisper_cpp_engine.model_name}).")
        try:
            words, segments = self.whisper_cpp_engine.transcribe(audio_path, language=self.language)
            return words, segments, "whisper.cpp"
        except Exception as e:
            logger.warning(f"whisper.cpp failed: {e}. Falling back to python whisper.")
            words, segments = self._transcribe_with_whisper(audio_path, beam_size, word_timestamps)
            return words, segments, "faster-whisper"

    def _transcribe_with_whisper(
        self,
        audio_path: str,
        beam_size: int = 5,
        word_timestamps: bool = True
    ) -> Tuple[List[WordTimestamp], List[Dict[str, Any]]]:
        self.load_whisper()
        logger.info(f"Transcribing audio with faster-whisper: {audio_path} in language '{self.language}'")

        segments_generator, info = self.whisper_model.transcribe(
            audio_path,
            language=self.language,
            beam_size=beam_size,
            word_timestamps=word_timestamps,
            vad_filter=False,
            condition_on_previous_text=True
        )

        all_words: List[WordTimestamp] = []
        raw_segments: List[Dict[str, Any]] = []

        for seg in segments_generator:
            seg_dict = {
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "avg_logprob": getattr(seg, "avg_logprob", 0.0),
                "no_speech_prob": getattr(seg, "no_speech_prob", 0.0)
            }
            raw_segments.append(seg_dict)

            if seg.words:
                for w in seg.words:
                    clean_word = w.word.strip()
                    if clean_word:
                        all_words.append(
                            WordTimestamp(
                                word=clean_word,
                                start=round(w.start, 3),
                                end=round(w.end, 3),
                                confidence=round(getattr(w, "probability", 0.95), 3)
                            )
                        )
            else:
                words = seg.text.strip().split()
                if words:
                    duration = max(0.1, seg.end - seg.start)
                    dt = duration / len(words)
                    for i, w in enumerate(words):
                        all_words.append(
                            WordTimestamp(
                                word=w,
                                start=round(seg.start + i * dt, 3),
                                end=round(seg.start + (i + 1) * dt, 3),
                                confidence=0.85
                            )
                        )

        logger.info(f"Faster-whisper ASR complete: {len(raw_segments)} segments, {len(all_words)} words.")
        return all_words, raw_segments

# Backward compatibility alias
BengaliASREngine = UnifiedASREngine
