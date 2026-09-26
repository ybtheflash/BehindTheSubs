import pytest
from src.models import WordTimestamp
from src.cue_segmenter import SubtitleCueSegmenter

def test_cue_segmentation_speaker_split():
    segmenter = SubtitleCueSegmenter()
    words = [
        WordTimestamp(word="তুই", start=1.0, end=1.5, speaker="SPEAKER_00"),
        WordTimestamp(word="অফিসে", start=1.6, end=2.0, speaker="SPEAKER_00"),
        WordTimestamp(word="না", start=2.5, end=3.0, speaker="SPEAKER_01"),
        WordTimestamp(word="আজকে", start=3.1, end=3.6, speaker="SPEAKER_01")
    ]
    cues = segmenter.segment(words)
    assert len(cues) == 2
    assert cues[0].speaker == "SPEAKER_00"
    assert cues[1].speaker == "SPEAKER_01"

def test_cue_segmentation_sentence_boundary():
    segmenter = SubtitleCueSegmenter(min_cue_duration=1.0)
    words = [
        WordTimestamp(word="আমি", start=1.0, end=1.5, speaker="SPEAKER_00"),
        WordTimestamp(word="কাল", start=1.6, end=2.0, speaker="SPEAKER_00"),
        WordTimestamp(word="আসব।", start=2.1, end=2.8, speaker="SPEAKER_00"),
        WordTimestamp(word="তুমি", start=3.2, end=3.8, speaker="SPEAKER_00"),
        WordTimestamp(word="থেকো।", start=3.9, end=4.5, speaker="SPEAKER_00")
    ]
    cues = segmenter.segment(words)
    assert len(cues) == 2
    assert "আমি কাল আসব।" in cues[0].text
    assert "তুমি থেকো।" in cues[1].text

def test_cue_segmentation_pause_split():
    segmenter = SubtitleCueSegmenter()
    words = [
        WordTimestamp(word="নমস্কার", start=1.0, end=2.2, speaker="SPEAKER_00"),
        # 1.5s silence gap
        WordTimestamp(word="কেমন", start=3.7, end=4.2, speaker="SPEAKER_00"),
        WordTimestamp(word="আছেন?", start=4.3, end=5.0, speaker="SPEAKER_00")
    ]
    cues = segmenter.segment(words)
    assert len(cues) == 2
