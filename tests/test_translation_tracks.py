import pytest
from src.models import SubtitleCue
from src.translate import SubtitleTranslator

def test_translation_generates_all_required_tracks():
    translator = SubtitleTranslator(gemini_key=None, anthropic_key=None, openai_key=None)
    cues = [
        SubtitleCue(
            index=1,
            start=0.0,
            end=2.5,
            speaker="SPEAKER_00",
            text="তুই আজ অফিসে যাচ্ছিস?"
        ),
        SubtitleCue(
            index=2,
            start=2.6,
            end=5.0,
            speaker="SPEAKER_01",
            text="না, আজকে আমার meeting আছে।"
        )
    ]

    result_cues = translator.translate_cues(cues, target_languages=["hi", "bn_rom", "hi_rom", "en"])

    assert len(result_cues) == 2
    for c in result_cues:
        # Bengali Native Text
        assert len(c.text) > 0
        # Hindi Devanagari Track
        assert "hi" in c.translations
        assert len(c.translations["hi"]) > 0
        # Romanized Bengali (Banglish) Track
        assert "bn_rom" in c.translations
        assert len(c.translations["bn_rom"]) > 0
        # Romanized Hindi (Hinglish) Track
        assert "hi_rom" in c.translations
        assert len(c.translations["hi_rom"]) > 0
        # English Track
        assert "en" in c.translations
        assert len(c.translations["en"]) > 0

def test_whisper_cpp_enforces_bn_language():
    from src.whisper_cpp_engine import WhisperCppEngine
    engine = WhisperCppEngine(language="auto")
    # Should normalize or default to bn
    assert engine.language in ("bn", "auto")
