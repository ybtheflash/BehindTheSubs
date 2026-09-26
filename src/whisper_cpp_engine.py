import os
import re
import json
import uuid
import shutil
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import httpx

from src.models import WordTimestamp
from src.config import default_config

logger = logging.getLogger(__name__)

class WhisperCppEngine:
    """
    Speech Recognition Engine powered by whisper.cpp (v1.9.4).
    Replaces default python faster-whisper with optimized C++ whisper.cpp AVX2 binary.

    Features:
    - Uses whisper-cli.exe / main.exe compiled for Windows x64
    - Token-level and word-level timestamp extraction (-ojf full JSON output)
    - Automatic GGML model acquisition from Hugging Face if missing
    - Configurable multi-threading and Bengali language support
    """

    HUGGINGFACE_MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

    def __init__(
        self,
        whisper_cpp_dir: Optional[Path] = None,
        model: Optional[str] = None,
        threads: Optional[int] = None,
        language: str = "bn"
    ):
        self.whisper_cpp_dir = Path(whisper_cpp_dir or (default_config.root_dir / "whisper.cpp-1.9.4")).resolve()
        self.model_name = (model or default_config.asr_model or "base").lower()
        # Map model names (e.g. small, base, tiny)
        if self.model_name.startswith("ggml-"):
            self.model_name = self.model_name.replace("ggml-", "").replace(".bin", "")
        self.threads = threads or int(os.getenv("WHISPER_CPP_THREADS", "4"))
        self.language = language or default_config.asr_language or "bn"

        self.cli_path: Optional[Path] = None
        self.model_path: Optional[Path] = None
        try:
            self.cli_path = self._locate_whisper_cli()
            self.model_path = self._ensure_model_exists(self.model_name)
        except Exception as e:
            logger.info(f"Local whisper.cpp engine not initialized ({e}). Cloud engines will be used.")

    def _locate_whisper_cli(self) -> Path:
        """
        Locates whisper-cli.exe or main.exe inside whisper.cpp-1.9.4.
        """
        candidates = [
            self.whisper_cpp_dir / "build" / "bin" / "Release" / "whisper-cli.exe",
            self.whisper_cpp_dir / "whisper-cli.exe",
            self.whisper_cpp_dir / "build" / "bin" / "Release" / "main.exe",
            self.whisper_cpp_dir / "main.exe",
            self.whisper_cpp_dir / "bin" / "whisper-cli.exe",
        ]

        for cand in candidates:
            if cand.exists():
                logger.info(f"Found whisper.cpp binary: {cand}")
                return cand

        # Fallback to PATH
        which_cli = shutil.which("whisper-cli") or shutil.which("main")
        if which_cli:
            return Path(which_cli)

        raise FileNotFoundError(
            f"Could not find whisper-cli.exe or main.exe in {self.whisper_cpp_dir}. "
            "Please ensure whisper.cpp-1.9.4 binaries are compiled or downloaded."
        )

    def _ensure_model_exists(self, model_name: str) -> Path:
        """
        Locates the GGML model in whisper.cpp-1.9.4/models or downloads it automatically.
        """
        models_dir = self.whisper_cpp_dir / "models"
        models_dir.mkdir(parents=True, exist_ok=True)

        model_file = models_dir / f"ggml-{model_name}.bin"
        if model_file.exists() and model_file.stat().st_size > 10_000_000:
            return model_file

        # Check for alternative available models if requested model is missing
        for fallback_name in ("base", "tiny", "small"):
            fallback_file = models_dir / f"ggml-{fallback_name}.bin"
            if fallback_file.exists() and fallback_file.stat().st_size > 10_000_000:
                logger.info(f"Requested model '{model_name}' missing, using available '{fallback_name}': {fallback_file}")
                return fallback_file

        # Download from Hugging Face
        logger.info(f"Downloading GGML model '{model_name}' to {model_file}...")
        url = f"{self.HUGGINGFACE_MODEL_URL}/ggml-{model_name}.bin"
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=180.0) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code} while downloading {url}")
                with open(model_file, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
            logger.info(f"Model downloaded successfully: {model_file.stat().st_size / (1024*1024):.1f} MB")
            return model_file
        except Exception as e:
            logger.warning(f"Failed to download ggml-{model_name}.bin: {e}. Checking for default ggml-base.bin...")
            default_base = models_dir / "ggml-base.bin"
            if default_base.exists() and default_base.stat().st_size > 10_000_000:
                return default_base
            raise RuntimeError(f"Could not find or download GGML model for whisper.cpp: {e}")

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        threads: Optional[int] = None
    ) -> Tuple[List[WordTimestamp], List[Dict[str, Any]]]:
        """
        Transcribes the given 16kHz mono audio file using whisper.cpp-1.9.4 CLI.
        Returns:
            - List[WordTimestamp]
            - List[Dict[str, Any]] (segments)
        """
        audio_p = Path(audio_path).resolve()
        if not audio_p.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if not self.cli_path or not self.model_path or not Path(self.cli_path).exists():
            raise RuntimeError(
                f"whisper.cpp executable or model not found at {self.whisper_cpp_dir}. "
                "Please use primary cloud ASR (bengali_xlsr, bengali_whisper, gemini)."
            )

        lang = (language or self.language or "bn").lower()
        if lang in ("bengali", "auto", "ben"):
            lang = "bn"
        th = threads or self.threads or 4

        temp_dir = default_config.temp_dir / "whisper_cpp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        out_prefix = temp_dir / f"wcpp_{uuid.uuid4().hex[:8]}"

        cmd = [
            str(self.cli_path),
            "-m", str(self.model_path),
            "-f", str(audio_p),
            "-l", lang,
            "--prompt", "বাংলা ভাষায় কথোপকথন এবং সংলাপ। Bengali dialogue with code-switched English and Hindi words.",
            "--carry-initial-prompt",
            "-t", str(th),
            "-ojf",
            "-of", str(out_prefix),
            "-sow",
            "-np"
        ]

        logger.info(f"Executing whisper.cpp: {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"whisper.cpp execution failed with code {e.returncode}: {e.stderr}")
            raise RuntimeError(f"whisper.cpp error: {e.stderr}")
        except Exception as e:
            logger.error(f"whisper.cpp process error: {e}")
            raise

        json_file = out_prefix.with_suffix(".json")
        if not json_file.exists():
            raise FileNotFoundError(f"Expected whisper.cpp output file not created: {json_file}")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            words, segments = self._parse_whisper_cpp_json(data)
            logger.info(f"whisper.cpp completed: {len(segments)} segments, {len(words)} words.")
            return words, segments
        finally:
            try:
                json_file.unlink(missing_ok=True)
            except Exception:
                pass

    def _parse_whisper_cpp_json(self, data: Dict[str, Any]) -> Tuple[List[WordTimestamp], List[Dict[str, Any]]]:
        """
        Parses whisper.cpp -ojf JSON format into standardized WordTimestamp objects and segments.
        """
        transcription = data.get("transcription", [])
        all_words: List[WordTimestamp] = []
        all_segments: List[Dict[str, Any]] = []

        for seg in transcription:
            offsets = seg.get("offsets", {})
            seg_start = round(offsets.get("from", 0) / 1000.0, 3)
            seg_end = round(offsets.get("to", 0) / 1000.0, 3)
            seg_text = seg.get("text", "").strip()

            all_segments.append({
                "start": seg_start,
                "end": seg_end,
                "text": seg_text,
                "avg_logprob": 0.95,
                "no_speech_prob": 0.05
            })

            tokens = seg.get("tokens", [])
            seg_words = self._tokens_to_words(tokens, seg_start, seg_end, seg_text)
            all_words.extend(seg_words)

        return all_words, all_segments

    def _tokens_to_words(
        self,
        tokens: List[Dict[str, Any]],
        seg_start: float,
        seg_end: float,
        seg_text: str
    ) -> List[WordTimestamp]:
        """
        Reconstructs words and timestamps from BPE tokens.
        Falls back to sequential interpolation if token list is missing.
        """
        words: List[WordTimestamp] = []

        curr_word = ""
        curr_start = None
        curr_end = None
        curr_conf_scores: List[float] = []

        for tok in tokens:
            raw_text = tok.get("text", "")
            # Skip special control tokens: [_BEG_], [_TT_500], etc.
            if raw_text.startswith("[_") and raw_text.endswith("]"):
                continue

            t_offsets = tok.get("offsets", {})
            t_start = round(t_offsets.get("from", 0) / 1000.0, 3)
            t_end = round(t_offsets.get("to", 0) / 1000.0, 3)
            t_prob = float(tok.get("p", 0.95))

            # In Whisper, a leading whitespace marks the start of a new word
            has_leading_space = raw_text.startswith(" ") or raw_text.startswith(" ") or raw_text.startswith("\t")
            cleaned_token = raw_text.strip()

            if not cleaned_token:
                continue

            if has_leading_space and curr_word:
                # Flush existing word
                avg_conf = round(sum(curr_conf_scores) / max(1, len(curr_conf_scores)), 3)
                words.append(
                    WordTimestamp(
                        word=curr_word,
                        start=curr_start if curr_start is not None else seg_start,
                        end=curr_end if curr_end is not None else seg_end,
                        confidence=avg_conf
                    )
                )
                curr_word = cleaned_token
                curr_start = t_start
                curr_end = t_end
                curr_conf_scores = [t_prob]
            else:
                if not curr_word:
                    curr_word = cleaned_token
                    curr_start = t_start
                    curr_end = t_end
                    curr_conf_scores = [t_prob]
                else:
                    curr_word += cleaned_token
                    curr_end = max(curr_end if curr_end is not None else t_end, t_end)
                    curr_conf_scores.append(t_prob)

        # Flush trailing word
        if curr_word:
            avg_conf = round(sum(curr_conf_scores) / max(1, len(curr_conf_scores)), 3)
            words.append(
                WordTimestamp(
                    word=curr_word,
                    start=curr_start if curr_start is not None else seg_start,
                    end=curr_end if curr_end is not None else seg_end,
                    confidence=avg_conf
                )
            )

        # Fallback if token reconstruction produced nothing
        if not words and seg_text:
            text_tokens = seg_text.split()
            if text_tokens:
                duration = max(0.1, seg_end - seg_start)
                dt = duration / len(text_tokens)
                for i, w in enumerate(text_tokens):
                    words.append(
                        WordTimestamp(
                            word=w,
                            start=round(seg_start + i * dt, 3),
                            end=round(seg_start + (i + 1) * dt, 3),
                            confidence=0.88
                        )
                    )

        return words
