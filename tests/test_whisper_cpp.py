import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.whisper_cpp_engine import WhisperCppEngine
from src.config import default_config
from src.models import WordTimestamp
from src.asr import UnifiedASREngine

def test_whisper_cpp_binary_located():
    engine = WhisperCppEngine()
    if not engine.cli_path:
        pytest.skip("whisper.cpp binary not compiled or directory removed")
    assert engine.cli_path.exists()
    assert engine.cli_path.name in ("whisper-cli.exe", "main.exe")

def test_whisper_cpp_model_path():
    engine = WhisperCppEngine(model="base")
    if not engine.model_path:
        pytest.skip("whisper.cpp model not downloaded or directory removed")
    assert engine.model_path.exists()
    assert engine.model_path.name == "ggml-base.bin"

def test_tokens_to_words_bpe_reconstruction():
    engine = WhisperCppEngine()
    tokens = [
        {"text": "[_BEG_]", "offsets": {"from": 0, "to": 0}, "p": 1.0},
        {"text": " আমি", "offsets": {"from": 100, "to": 400}, "p": 0.96},
        {"text": " কাল", "offsets": {"from": 450, "to": 800}, "p": 0.94},
        {"text": " আস", "offsets": {"from": 850, "to": 1100}, "p": 0.95},
        {"text": "ব।", "offsets": {"from": 1100, "to": 1300}, "p": 0.98},
        {"text": "[_TT_500]", "offsets": {"from": 1300, "to": 1300}, "p": 0.99},
    ]

    words = engine._tokens_to_words(tokens, seg_start=0.1, seg_end=1.3, seg_text="আমি কাল আসব।")
    assert len(words) == 3
    assert words[0].word == "আমি"
    assert words[0].start == 0.1
    assert words[0].end == 0.4

    assert words[1].word == "কাল"
    assert words[1].start == 0.45
    assert words[1].end == 0.8

    assert words[2].word == "আসব।"
    assert words[2].start == 0.85
    assert words[2].end == 1.3

def test_whisper_cpp_transcribe_mock(tmp_path):
    wav_file = tmp_path / "mock.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = WhisperCppEngine()
    if not engine.cli_path or not engine.cli_path.exists():
        dummy_cli = tmp_path / "whisper-cli.exe"
        dummy_cli.write_text("dummy", encoding="utf-8")
        dummy_model = tmp_path / "ggml-base.bin"
        dummy_model.write_text("dummy", encoding="utf-8")
        engine.cli_path = dummy_cli
        engine.model_path = dummy_model

    mock_json = {
        "transcription": [
            {
                "offsets": {"from": 0, "to": 1500},
                "text": "নমস্কার",
                "tokens": [
                    {"text": " নমস্কার", "offsets": {"from": 100, "to": 1400}, "p": 0.98}
                ]
            }
        ]
    }

    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        # Intercept output json creation
        def side_effect(*args, **kwargs):
            cmd = args[0]
            of_idx = cmd.index("-of")
            prefix = Path(cmd[of_idx + 1])
            with open(prefix.with_suffix(".json"), "w", encoding="utf-8") as f:
                import json
                json.dump(mock_json, f)
            return mock_proc

        mock_run.side_effect = side_effect

        words, segs = engine.transcribe(str(wav_file))

        assert len(segs) == 1
        assert segs[0]["text"] == "নমস্কার"
        assert len(words) == 1
        assert words[0].word == "নমস্কার"

def test_unified_asr_uses_whisper_cpp(tmp_path):
    wav_file = tmp_path / "mock.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = UnifiedASREngine()

    with patch.object(engine.whisper_cpp_engine, "transcribe") as mock_cpp:
        mock_cpp.return_value = (
            [WordTimestamp(word="টেস্ট", start=0.0, end=1.0, confidence=0.95)],
            [{"start": 0.0, "end": 1.0, "text": "টেস্ট"}]
        )

        words, segs, used = engine.transcribe(str(wav_file), provider="whisper.cpp")
        assert used == "whisper.cpp"
        assert len(words) == 1
        assert words[0].word == "টেস্ট"
