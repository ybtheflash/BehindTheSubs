from pathlib import Path
from typing import List
from src.models import SubtitleCue

def format_vtt_timestamp(seconds: float) -> str:
    """
    Formats float seconds into WebVTT timestamp: HH:MM:SS.mmm
    """
    total_ms = int(round(max(0.0, seconds) * 1000))
    hours = total_ms // 3600000
    minutes = (total_ms % 3600000) // 60000
    secs = (total_ms % 60000) // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

def write_vtt(cues: List[SubtitleCue], output_path: str, include_speaker: bool = True) -> str:
    """
    Writes SubtitleCue objects to a standard WebVTT file with UTF-8 encoding.
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    lines = ["WEBVTT", ""]

    for cue in cues:
        start_ts = format_vtt_timestamp(cue.start)
        end_ts = format_vtt_timestamp(cue.end)
        lines.append(f"{start_ts} --> {end_ts}")
        if include_speaker and cue.speaker:
            lines.append(f"[{cue.speaker}]")
        lines.append(cue.text)
        lines.append("")

    content = "\n".join(lines)
    with open(out_p, "w", encoding="utf-8") as f:
        f.write(content)

    return str(out_p)
