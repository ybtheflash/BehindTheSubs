import logging
from typing import List, Tuple, Dict, Any
import numpy as np
import soundfile as sf
from faster_whisper.vad import get_speech_timestamps, VadOptions
from src.models import VADSegment

logger = logging.getLogger(__name__)

class VADDetector:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.vad_options = VadOptions(
            threshold=0.5,
            min_speech_duration_ms=250,
            max_speech_duration_s=float("inf"),
            min_silence_duration_ms=2000,
            speech_pad_ms=400
        )

    def detect_speech(self, audio_path: str) -> List[VADSegment]:
        """
        Runs Silero VAD over the 16kHz mono audio and returns a list of speech segments with start and end in seconds.
        """
        logger.info(f"Running VAD on {audio_path}")
        audio, sr = sf.read(audio_path, dtype="float32")
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        if sr != self.sample_rate:
            # Resample if needed
            import scipy.signal
            num_samples = int(len(audio) * self.sample_rate / sr)
            audio = scipy.signal.resample(audio, num_samples)

        # Get speech timestamps in samples
        speech_chunks = get_speech_timestamps(audio, vad_options=self.vad_options, sampling_rate=self.sample_rate)
        
        segments: List[VADSegment] = []
        for chunk in speech_chunks:
            start_sec = round(chunk["start"] / self.sample_rate, 3)
            end_sec = round(chunk["end"] / self.sample_rate, 3)
            segments.append(VADSegment(start=start_sec, end=end_sec, speech_prob=1.0))

        logger.info(f"VAD detected {len(segments)} speech segments")
        return segments

    @staticmethod
    def compute_overlap_ratio(
        cue_start: float,
        cue_end: float,
        speech_segments: List[VADSegment]
    ) -> Tuple[float, float]:
        """
        Computes the total speech overlap (in seconds) and the overlap ratio (0.0 to 1.0)
        for a given time interval [cue_start, cue_end].
        Returns (overlap_seconds, overlap_ratio).
        """
        duration = max(0.001, cue_end - cue_start)
        total_overlap = 0.0

        for seg in speech_segments:
            # Check interval intersection: max(start1, start2) to min(end1, end2)
            overlap_start = max(cue_start, seg.start)
            overlap_end = min(cue_end, seg.end)
            if overlap_end > overlap_start:
                total_overlap += (overlap_end - overlap_start)

        overlap_ratio = min(1.0, total_overlap / duration)
        return round(total_overlap, 3), round(overlap_ratio, 3)
