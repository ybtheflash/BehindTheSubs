import subprocess
import json
import logging
from pathlib import Path
from typing import Tuple, Optional
import soundfile as sf

logger = logging.getLogger(__name__)

def extract_audio(
    video_path: str,
    output_audio_path: Optional[str] = None,
    sample_rate: int = 16000,
    channels: int = 1
) -> str:
    """
    Extracts audio from a video file using FFmpeg, converted to mono WAV at the specified sample rate.
    """
    video_p = Path(video_path)
    if not video_p.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_audio_path is None:
        output_audio_p = video_p.with_suffix(".wav")
    else:
        output_audio_p = Path(output_audio_path)

    output_audio_p.parent.mkdir(parents=True, exist_ok=True)

    # Use ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",               # overwrite
        "-i", str(video_p),
        "-vn",              # disable video
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        str(output_audio_p)
    ]

    logger.info(f"Extracting audio: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg audio extraction failed: {result.stderr}")
        raise RuntimeError(f"FFmpeg extraction failed: {result.stderr[-500:]}")

    logger.info(f"Audio extracted successfully to {output_audio_p}")
    return str(output_audio_p)

def get_audio_info(audio_path: str) -> dict:
    """
    Returns metadata about an audio file (duration, sample_rate, channels, frames).
    """
    try:
        with sf.SoundFile(audio_path) as f:
            duration = len(f) / float(f.samplerate)
            return {
                "duration": round(duration, 3),
                "samplerate": f.samplerate,
                "channels": f.channels,
                "frames": len(f),
                "format": f.format,
                "subtype": f.subtype
            }
    except Exception as e:
        logger.warning(f"SoundFile inspection failed, falling back to ffprobe: {e}")
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            audio_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            format_info = data.get("format", {})
            return {
                "duration": float(format_info.get("duration", 0.0)),
                "samplerate": 16000,
                "channels": 1
            }
        return {"duration": 0.0, "samplerate": 16000, "channels": 1}
