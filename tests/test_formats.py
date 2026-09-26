import pytest
from pathlib import Path
from src.models import SubtitleCue
from src.formats.vtt_writer import format_vtt_timestamp, write_vtt
from src.formats.srt_writer import format_srt_timestamp, write_srt

def test_vtt_timestamp_format():
    assert format_vtt_timestamp(0.0) == "00:00:00.000"
    assert format_vtt_timestamp(4.12) == "00:00:04.120"
    assert format_vtt_timestamp(3661.055) == "01:01:01.055"

def test_srt_timestamp_format():
    assert format_srt_timestamp(0.0) == "00:00:00,000"
    assert format_srt_timestamp(4.12) == "00:00:04,120"
    assert format_srt_timestamp(3661.055) == "01:01:01,055"

def test_vtt_writer_output(tmp_path):
    cues = [
        SubtitleCue(
            index=1,
            start=4.12,
            end=6.80,
            speaker="SPEAKER_00",
            text="তুই আজ অফিসে যাচ্ছিস?"
        ),
        SubtitleCue(
            index=2,
            start=7.00,
            end=9.50,
            speaker="SPEAKER_01",
            text="না, আজকে আমার meeting আছে।"
        )
    ]
    out_file = tmp_path / "test.vtt"
    write_vtt(cues, str(out_file))

    content = out_file.read_text(encoding="utf-8")
    assert content.startswith("WEBVTT")
    assert "00:00:04.120 --> 00:00:06.800" in content
    assert "[SPEAKER_00]" in content
    assert "তুই আজ অফিসে যাচ্ছিস?" in content
    assert "00:00:07.000 --> 00:00:09.500" in content

def test_srt_writer_output(tmp_path):
    cues = [
        SubtitleCue(
            index=1,
            start=4.12,
            end=6.80,
            speaker="SPEAKER_00",
            text="তুই আজ অফিসে যাচ্ছিস?",
            translations={"en": "Are you going to the office today?"}
        )
    ]
    out_file = tmp_path / "test.srt"
    write_srt(cues, str(out_file), language_key="en")

    content = out_file.read_text(encoding="utf-8")
    assert "1" in content
    assert "00:00:04,120 --> 00:00:06,800" in content
    assert "Are you going to the office today?" in content
