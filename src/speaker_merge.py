import logging
from typing import List, Tuple
from src.models import WordTimestamp, SpeakerSegment

logger = logging.getLogger(__name__)

class SpeakerWordReconciler:
    """
    Reconciles word-level timestamps with speaker diarization segments.
    Assigns stable speaker identities to each word based on maximum temporal overlap.
    """

    @staticmethod
    def reconcile(
        words: List[WordTimestamp],
        diarization_segments: List[SpeakerSegment]
    ) -> List[WordTimestamp]:
        if not words:
            return []

        if not diarization_segments:
            # Fallback to SPEAKER_00 if no diarization segments exist
            for w in words:
                w.speaker = "SPEAKER_00"
            return words

        last_known_speaker = diarization_segments[0].speaker

        for word in words:
            best_speaker = None
            max_overlap = 0.0

            # Find overlapping diarization segments
            for d_seg in diarization_segments:
                overlap_start = max(word.start, d_seg.start)
                overlap_end = min(word.end, d_seg.end)
                overlap = max(0.0, overlap_end - overlap_start)

                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = d_seg.speaker

            # If no direct overlap, find closest diarization segment within proximity
            if best_speaker is None or max_overlap < 0.01:
                closest_dist = float("inf")
                closest_speaker = last_known_speaker
                word_mid = (word.start + word.end) / 2.0

                for d_seg in diarization_segments:
                    seg_mid = (d_seg.start + d_seg.end) / 2.0
                    dist = abs(word_mid - seg_mid)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_speaker = d_seg.speaker

                best_speaker = closest_speaker

            word.speaker = best_speaker
            last_known_speaker = best_speaker

        logger.info(f"Reconciled {len(words)} words with speaker identities.")
        return words
