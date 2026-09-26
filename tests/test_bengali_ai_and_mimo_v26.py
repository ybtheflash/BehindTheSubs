import pytest
from unittest.mock import patch, MagicMock
from src.bengali_ai_asr import BengaliAIASREngine
from src.translate import SubtitleTranslator
from src.models import SubtitleCue
from src.asr import UnifiedASREngine

def test_bengali_ai_words_from_text():
    engine = BengaliAIASREngine()
    text = "আমি কালকে অফিসে যাব এবং একটা আর্জেন্ট মিটিং আছে।"
    words = engine._words_from_text(text, 0.0, 5.0)
    assert len(words) == 9
    assert words[0].word == "আমি"
    assert words[-1].word == "আছে।"
    assert words[0].start >= 0.0
    assert words[-1].end <= 5.0

def test_bengali_ai_transcribe_modal_primary(tmp_path):
    """
    Tests that Modal Primary endpoint is used first when available.
    """
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = BengaliAIASREngine()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "মোডাল প্রাইমারি দিয়ে সফলভাবে ট্রান্সক্রাইব হয়েছে।"}

    with patch("requests.post", return_value=mock_resp) as mock_post, \
         patch.object(engine, "_get_client") as mock_gradio:
        words, segments = engine.transcribe(str(wav_file))
        assert mock_post.called
        assert not mock_gradio.called
        assert len(words) > 0
        assert segments[0]["text"] == "মোডাল প্রাইমারি দিয়ে সফলভাবে ট্রান্সক্রাইব হয়েছে।"

def test_bengali_ai_transcribe_gradio_fallback(tmp_path):
    """
    Tests that if Modal endpoint fails or is unavailable, it falls back to Gradio HF spaces.
    """
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = BengaliAIASREngine()
    engine.modal_whisper_url = None  # Simulate modal offline
    mock_client = MagicMock()
    mock_client.predict.return_value = "এই যে কালকে দেখা হবে।"

    with patch.object(engine, "_get_client", return_value=mock_client):
        words, segments = engine.transcribe(str(wav_file))
        assert len(words) == 5
        assert len(segments) == 1
        assert segments[0]["text"] == "এই যে কালকে দেখা হবে।"

def test_unified_asr_uses_bengali_ai_by_default(tmp_path):
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = UnifiedASREngine(default_provider="bengali_ai")
    with patch.object(engine.bengali_ai_engine, "transcribe_whisper") as mock_bai:
        from src.models import WordTimestamp
        mock_bai.return_value = ([WordTimestamp(word="টেস্ট", start=0.0, end=1.0)], [{"text": "টেস্ট"}])
        words, segs, used = engine.transcribe(str(wav_file))
        assert used in ("bengali_whisper", "bengali_ai")
        assert len(words) == 1

def test_mimo_v26_flash_translation_structure():
    translator = SubtitleTranslator(mimo_key="test_key")
    cues = [
        SubtitleCue(index=1, start=0.0, end=2.0, text="আমি কাল অফিসে আসব।", speaker="SPEAKER_00")
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"results": [{"id": 1, "hi": "मैं कल ऑफिस आऊंगा।", "bn_rom": "Ami kal office-e ashbo.", "hi_rom": "Main kal office aunga.", "en": "I will come to the office tomorrow."}]}'
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        res = translator.translate_cues(cues, ["hi", "bn_rom", "hi_rom", "en"])
        call_json = mock_post.call_args[1]["json"]
        # Verify primary model is mimo-v2.6-flash
        assert call_json["model"] == "mimo-v2.6-flash"
        assert res[0].translations["bn_rom"] == "Ami kal office-e ashbo."
        assert res[0].translations["hi"] == "मैं कल ऑफिस आऊंगा।"
        assert res[0].translations["hi_rom"] == "Main kal office aunga."
        assert res[0].translations["en"] == "I will come to the office tomorrow."

def test_bengali_ai_auto_extracts_audio_from_video(tmp_path):
    """
    Guarantees that video files (.mp4, .mkv, etc.) are never sent directly to Gradio client.
    Audio must be extracted first to mono WAV.
    """
    video_file = tmp_path / "sample_video.mp4"
    video_file.write_text("dummy video content", encoding="utf-8")

    dummy_wav = tmp_path / "extracted.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(dummy_wav), np.zeros(16000), 16000)

    engine = BengaliAIASREngine()
    engine.modal_whisper_url = None  # Test Gradio extraction path
    mock_client = MagicMock()
    mock_client.predict.return_value = "ভিডিও থেকে অডিও এক্সট্র্যাক্ট হয়েছে।"

    with patch("src.bengali_ai_asr.extract_audio") as mock_extract, \
         patch.object(engine, "_get_client", return_value=mock_client), \
         patch("gradio_client.handle_file") as mock_hf:
        
        # When extract_audio is called, copy dummy_wav to the destination so sf.SoundFile can read it
        def fake_extract(src, dst, **kwargs):
            import shutil
            shutil.copy(str(dummy_wav), str(dst))
            return str(dst)
        mock_extract.side_effect = fake_extract

        words, segments = engine.transcribe(str(video_file))

        # Must have called extract_audio because input was .mp4
        assert mock_extract.called
        assert len(words) > 0
        assert segments[0]["text"] == "ভিডিও থেকে অডিও এক্সট্র্যাক্ট হয়েছে।"

        # Gradio handle_file MUST have received a .wav file, NEVER .mp4
        hf_arg = mock_hf.call_args[0][0]
        assert hf_arg.endswith(".wav")
        assert not hf_arg.endswith(".mp4")

def test_bengali_ai_failover_from_ybtheflash_to_bengaliai(tmp_path):
    """
    Tests that if ybtheflash (/transcribe_mic) errors (e.g. ZeroGPU quota),
    it automatically falls back to bengaliAI (/transcribe).
    """
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = BengaliAIASREngine()
    engine.modal_whisper_url = None  # Test Gradio failover path

    mock_client_yb = MagicMock()
    mock_client_yb.predict.side_effect = RuntimeError("ZeroGPU duration exceeded")

    mock_client_bengaliai = MagicMock()
    mock_client_bengaliai.predict.return_value = "বাংলা এআই থেকে সফল ফল।"

    def get_client_side_effect(space_id):
        if "ybtheflash" in space_id:
            return mock_client_yb
        return mock_client_bengaliai

    with patch.object(engine, "_get_client", side_effect=get_client_side_effect):
        words, segments = engine.transcribe(str(wav_file))
        assert len(words) > 0
        assert segments[0]["text"] == "বাংলা এআই থেকে সফল ফল।"

def test_bengali_xlsr_modal_primary(tmp_path):
    """
    Tests that Modal Primary endpoint is used first for XLS-R.
    """
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = BengaliAIASREngine()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "এক্স এল এস আর মোডাল প্রাইমারি ফল।"}

    with patch("requests.post", return_value=mock_resp) as mock_post, \
         patch.object(engine, "_get_client") as mock_gradio:
        words, segments = engine.transcribe_xlsr(str(wav_file))
        assert mock_post.called
        assert not mock_gradio.called
        assert len(words) > 0
        assert segments[0]["text"] == "এক্স এল এস আর মোডাল প্রাইমারি ফল।"

def test_bengali_xlsr_transcribe_mock(tmp_path):
    """
    Tests ybtheflash/bengali-asr (Wav2Vec2 XLS-R 300M) prediction via Gradio fallback.
    """
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = BengaliAIASREngine()
    engine.modal_xlsr_url = None  # Simulate modal offline to test Gradio fallback
    mock_client = MagicMock()
    mock_client.predict.return_value = ("এক্স এল এস আর মডেল দ্বারা ট্রানস্ক্রাইবড।", {"model": "xlsr"})

    with patch.object(engine, "_get_client", return_value=mock_client):
        words, segments = engine.transcribe_xlsr(str(wav_file))
        assert len(words) > 0
        assert segments[0]["text"] == "এক্স এল এস আর মডেল দ্বারা ট্রানস্ক্রাইবড।"
        mock_client.predict.assert_called_once()
        assert mock_client.predict.call_args[1]["api_name"] == "/transcribe"
        assert mock_client.predict.call_args[1]["model_key"] == "xlsr"

def test_unified_asr_uses_bengali_xlsr(tmp_path):
    wav_file = tmp_path / "test.wav"
    import soundfile as sf
    import numpy as np
    sf.write(str(wav_file), np.zeros(16000), 16000)

    engine = UnifiedASREngine(default_provider="bengali_xlsr")
    with patch.object(engine.bengali_ai_engine, "transcribe_xlsr") as mock_xlsr:
        from src.models import WordTimestamp
        mock_xlsr.return_value = ([WordTimestamp(word="টেস্ট", start=0.0, end=1.0)], [{"text": "টেস্ট"}])
        words, segs, used = engine.transcribe(str(wav_file), provider="bengali_xlsr")
        assert used == "bengali_xlsr"
        assert len(words) == 1


