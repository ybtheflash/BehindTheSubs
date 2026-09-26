import pytest
import os
from unittest.mock import patch, MagicMock
from src.mimo_asr import MiMoASREngine
from src.config import PipelineConfig
from src.asr import UnifiedASREngine

def test_mimo_key_pool_parsing():
    cfg = PipelineConfig(
        mimo_api_key="key_primary",
        mimo_api_keys_raw="key_secondary, key_tertiary\nkey_quaternary"
    )
    keys = cfg.get_mimo_keys()
    assert "key_primary" in keys
    assert "key_secondary" in keys
    assert "key_tertiary" in keys
    assert "key_quaternary" in keys
    assert len(keys) == 4

def test_mimo_masked_keys():
    cfg = PipelineConfig(
        mimo_api_key="sk-mimo-test-secret-12345",
        mimo_api_keys_raw="sk-mimo-second-secret-67890"
    )
    masked = cfg.get_masked_mimo_keys()
    assert len(masked) == 2
    assert masked[0]["label"].startswith("Key 1 (sk-m...")
    assert masked[0]["value"] == "sk-mimo-test-secret-12345"

def test_mimo_key_rotation():
    engine = MiMoASREngine(api_keys=["key1", "key2", "key3"])
    assert engine.get_current_key() == "key1"
    engine.rotate_key()
    assert engine.get_current_key() == "key2"
    engine.rotate_key()
    assert engine.get_current_key() == "key3"
    engine.rotate_key()
    assert engine.get_current_key() == "key1"

def test_mimo_api_payload_structure(tmp_path):
    # Create dummy 1-second wav
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = MiMoASREngine(api_keys=["test_key"])

    # Mock httpx client response
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "আমি কাল আসব।"}}]
        }
        mock_post.return_value = mock_resp

        words, segs = engine.transcribe(str(wav_file))

        # Check call arguments
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        headers = call_args[1]["headers"]

        assert payload["model"] == "mimo-v2.5-asr"
        assert headers["api-key"] == "test_key"
        assert payload["messages"][0]["role"] == "system"
        assert "Bengali" in payload["messages"][0]["content"]
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"][0]["type"] == "input_audio"
        assert payload["messages"][1]["content"][0]["input_audio"]["data"].startswith("data:audio/wav;base64,")
        assert payload["asr_options"]["language"] == "auto"
        assert len(words) == 3  # "আমি", "কাল", "আসব।"
        assert words[0].word == "আমি"

def test_unified_asr_fallback_to_whisper(tmp_path):
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    # Engine with invalid MiMo key
    engine = UnifiedASREngine(default_provider="mimo")
    engine.mimo_engine.api_keys = []

    # Should fallback gracefully to whisper.cpp without crashing
    with patch.object(engine.whisper_cpp_engine, "transcribe") as mock_cpp:
        from src.models import WordTimestamp
        mock_cpp.return_value = ([WordTimestamp(word="টেস্ট", start=0.0, end=1.0)], [])

        words, segs, used = engine.transcribe(str(wav_file), provider="mimo")
        assert used == "whisper.cpp"
        assert len(words) == 1
