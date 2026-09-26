import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file from root directory
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

@dataclass
class PipelineConfig:
    # Root paths
    root_dir: Path = ROOT_DIR
    output_dir: Path = ROOT_DIR / "outputs"
    artifacts_dir: Path = ROOT_DIR / "artifacts"
    temp_dir: Path = ROOT_DIR / "temp"

    # API Keys
    hf_token: str = os.getenv("HF_TOKEN", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_api_keys_raw: str = os.getenv("GEMINI_API_KEYS", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    # ASR Provider: 'bengali_ai' (bengaliAI Regional Whisper Medium), 'gemini' (gemini-flash-latest), or 'whisper.cpp' (whisper.cpp-1.9.4 C++ AVX2)
    asr_provider: str = os.getenv("ASR_PROVIDER", "bengali_ai")

    # Xiaomi MiMo ASR Settings
    mimo_api_key: str = os.getenv("MIMO_API_KEY", "")
    mimo_api_keys_raw: str = os.getenv("MIMO_API_KEYS", "")
    mimo_base_url: str = os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")
    mimo_model: str = os.getenv("MIMO_MODEL", "mimo-v2.5-asr")

    # whisper.cpp-1.9.4 Settings
    whisper_cpp_dir: Path = ROOT_DIR / "whisper.cpp-1.9.4"
    whisper_cpp_model: str = os.getenv("WHISPER_CPP_MODEL", "base")
    whisper_cpp_threads: int = int(os.getenv("WHISPER_CPP_THREADS", "4"))

    # Local fallback / model settings
    asr_model: str = os.getenv("ASR_MODEL", "base")
    asr_device: str = os.getenv("ASR_DEVICE", "cpu")
    asr_compute_type: str = os.getenv("ASR_COMPUTE_TYPE", "int8")
    asr_language: str = os.getenv("ASR_LANGUAGE", "bn")

    # Diarization Settings
    diarization_model: str = os.getenv("DIARIZATION_MODEL", "pyannote/speaker-diarization-community-1")
    enable_diarization: bool = os.getenv("ENABLE_DIARIZATION", "true").lower() in ("true", "1", "yes")

    # Subtitle presentation constraints
    max_cps: float = float(os.getenv("MAX_CPS", "17.0"))
    max_lines: int = int(os.getenv("MAX_LINES", "2"))
    max_chars_per_line: int = int(os.getenv("MAX_CHARS_PER_LINE", "42"))
    min_cue_duration: float = float(os.getenv("MIN_CUE_DURATION", "1.0"))
    max_cue_duration: float = float(os.getenv("MAX_CUE_DURATION", "7.0"))

    # QC Thresholds
    hallucination_high_threshold: float = float(os.getenv("HALLUCINATION_HIGH_THRESHOLD", "0.35"))
    hallucination_medium_threshold: float = float(os.getenv("HALLUCINATION_MEDIUM_THRESHOLD", "0.65"))
    asr_confidence_low_threshold: float = float(os.getenv("ASR_CONFIDENCE_LOW_THRESHOLD", "0.60"))

    # Server settings
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_mimo_keys(self) -> list[str]:
        """
        Gathers all configured MiMo API keys from:
        - MIMO_API_KEY
        - MIMO_API_KEYS (comma or space separated)
        - MIMO_API_KEY_1, MIMO_API_KEY_2, etc.
        """
        keys = []
        # Single key
        if self.mimo_api_key.strip():
            keys.append(self.mimo_api_key.strip())

        # Comma / newline separated keys
        if self.mimo_api_keys_raw.strip():
            for k in self.mimo_api_keys_raw.replace("\n", ",").replace(";", ",").split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)

        # Numbered keys: MIMO_API_KEY_1, MIMO_API_KEY_2, ...
        for env_k, env_v in os.environ.items():
            if env_k.startswith("MIMO_API_KEY_") and env_v.strip():
                v = env_v.strip()
                if v not in keys:
                    keys.append(v)

        return keys

    def get_masked_mimo_keys(self) -> list[dict]:
        """
        Returns list of dicts with masked key display strings for safe UI selection.
        """
        keys = self.get_mimo_keys()
        res = []
        for i, k in enumerate(keys, 1):
            if len(k) > 8:
                masked = f"{k[:4]}...{k[-4:]}"
            else:
                masked = f"Key #{i} (configured)"
            res.append({"id": f"key_{i}", "label": f"Key {i} ({masked})", "value": k})
        return res

    def get_gemini_keys(self) -> list[str]:
        """
        Gathers all configured Google Gemini API keys from:
        - GEMINI_API_KEY
        - GEMINI_API_KEYS (comma or semicolon separated)
        - GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
        """
        keys = []
        if self.gemini_api_key.strip():
            keys.append(self.gemini_api_key.strip())

        if self.gemini_api_keys_raw.strip():
            for k in self.gemini_api_keys_raw.replace("\n", ",").replace(";", ",").split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)

        for env_k, env_v in os.environ.items():
            if env_k.startswith("GEMINI_API_KEY_") and env_v.strip():
                v = env_v.strip()
                if v not in keys:
                    keys.append(v)

        return keys

    def get_masked_gemini_keys(self) -> list[dict]:
        """
        Returns list of dicts with masked Gemini key display strings for safe UI selection.
        """
        keys = self.get_gemini_keys()
        res = []
        for i, k in enumerate(keys, 1):
            if len(k) > 8:
                masked = f"{k[:4]}...{k[-4:]}"
            else:
                masked = f"Key #{i} (configured)"
            res.append({"id": f"gemini_key_{i}", "label": f"Gemini Key {i} ({masked})", "value": k})
        return res

# Default configuration instance
default_config = PipelineConfig()
