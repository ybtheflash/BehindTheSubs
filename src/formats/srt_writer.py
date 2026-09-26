from pathlib import Path
from typing import List, Optional
from src.models import SubtitleCue

def format_srt_timestamp(seconds: float) -> str:
    """
    Formats float seconds into SubRip SRT timestamp: HH:MM:SS,mmm
    """
    total_ms = int(round(max(0.0, seconds) * 1000))
    hours = total_ms // 3600000
    minutes = (total_ms % 3600000) // 60000
    secs = (total_ms % 60000) // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def write_srt(
    cues: List[SubtitleCue],
    output_path: str,
    language_key: Optional[str] = None
) -> str:
    """
    Writes SubtitleCue objects to a standard SubRip (.srt) file.
    If language_key is specified, writes the corresponding translation (e.g. 'en', 'hi'),
    otherwise writes the primary cue text.
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for i, cue in enumerate(cues, start=1):
        start_ts = format_srt_timestamp(cue.start)
        end_ts = format_srt_timestamp(cue.end)
        
        text = cue.text
        if language_key and language_key in cue.translations:
            text = cue.translations[language_key]

        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(text)
        lines.append("")

    content = "\n".join(lines)
    with open(out_p, "w", encoding="utf-8") as f:
        f.write(content)

    return str(out_p)
