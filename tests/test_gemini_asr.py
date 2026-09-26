import pytest
from unittest.mock import patch, MagicMock
from src.gemini_asr import GeminiASREngine
from src.config import PipelineConfig
from src.asr import UnifiedASREngine
from src.models import WordTimestamp

import os

def test_gemini_key_pool_parsing():
    with patch.dict(os.environ, {}, clear=True):
        cfg = PipelineConfig(
            gemini_api_key="AIzaSy_key_primary",
            gemini_api_keys_raw="AIzaSy_key_2, AIzaSy_key_3\nAIzaSy_key_4"
        )
        keys = cfg.get_gemini_keys()
        assert "AIzaSy_key_primary" in keys
        assert "AIzaSy_key_2" in keys
        assert "AIzaSy_key_3" in keys
        assert "AIzaSy_key_4" in keys
        assert len(keys) == 4

def test_gemini_masked_keys():
    with patch.dict(os.environ, {}, clear=True):
        cfg = PipelineConfig(
            gemini_api_key="AIzaSyTestSecretKey12345678",
            gemini_api_keys_raw="AIzaSySecondSecretKey87654321"
        )
        masked = cfg.get_masked_gemini_keys()
        assert len(masked) == 2
        assert masked[0]["label"].startswith("Gemini Key 1 (AIza...5678)")
        assert masked[0]["value"] == "AIzaSyTestSecretKey12345678"

def test_gemini_key_rotation():
    engine = GeminiASREngine(api_keys=["gkey1", "gkey2", "gkey3"], model="gemini-flash-latest")
    assert engine.get_current_key() == "gkey1"
    engine.rotate_key()
    assert engine.get_current_key() == "gkey2"
    engine.rotate_key()
    assert engine.get_current_key() == "gkey3"
    engine.rotate_key()
    assert engine.get_current_key() == "gkey1"

def test_gemini_api_payload_and_json_parsing(tmp_path):
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = GeminiASREngine(api_keys=["test_gemini_key"], model="gemini-flash-latest")

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{\n  "transcript": "তুই আজ অফিসে যাচ্ছিস?",\n  "segments": [\n    {"start": 0.0, "end": 1.0, "text": "তুই আজ অফিসে যাচ্ছিস?"}\n  ]\n}'
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        words, segs = engine.transcribe(str(wav_file))

        call_args = mock_post.call_args
        url = call_args[0][0]
        payload = call_args[1]["json"]

        assert "gemini-flash-latest:generateContent?key=test_gemini_key" in url
        assert payload["contents"][0]["parts"][0]["inlineData"]["mimeType"] == "audio/wav"
        assert payload["generationConfig"]["responseMimeType"] == "application/json"

        assert len(words) == 4  # "তুই", "আজ", "অফিসে", "যাচ্ছিস?"
        assert words[0].word == "তুই"
        assert words[2].word == "অফিসে"
        assert words[0].start == 0.0
        assert words[-1].end == 1.0

def test_gemini_plain_text_fallback_parsing(tmp_path):
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = GeminiASREngine(api_keys=["test_gemini_key"], model="gemini-flash-latest")

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "আমি কাল আসব।"
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        words, segs = engine.transcribe(str(wav_file))
        assert len(words) == 3
        assert words[0].word == "আমি"
        assert words[1].word == "কাল"
        assert words[2].word == "আসব।"

def test_unified_asr_gemini_success(tmp_path):
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = UnifiedASREngine()

    with patch.object(engine.gemini_engine, "transcribe") as mock_gemini:
        mock_gemini.return_value = (
            [WordTimestamp(word="নমস্কার", start=0.0, end=0.8, confidence=0.98)],
            [{"start": 0.0, "end": 0.8, "text": "নমস্কার"}]
        )

        words, segs, used = engine.transcribe(str(wav_file), provider="gemini")
        assert used == "gemini"
        assert len(words) == 1
        assert words[0].word == "নমস্কার"

def test_unified_asr_gemini_fallback_to_whisper(tmp_path):
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = UnifiedASREngine()

    with patch.object(engine.gemini_engine, "transcribe", side_effect=RuntimeError("Gemini Quota Exceeded")):
        with patch.object(engine.whisper_cpp_engine, "transcribe") as mock_cpp:
            mock_cpp.return_value = (
                [WordTimestamp(word="হাঁ", start=0.0, end=0.5, confidence=0.88)],
                [{"start": 0.0, "end": 0.5, "text": "হাঁ"}]
            )

            words, segs, used = engine.transcribe(str(wav_file), provider="gemini")
            assert used == "whisper.cpp"
            assert len(words) == 1
            assert words[0].word == "হাঁ"
