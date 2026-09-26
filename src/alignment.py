import logging
from typing import List
from src.models import WordTimestamp

logger = logging.getLogger(__name__)

class WordAlignmentProcessor:
    """
    Sanitizes, validates, and refines word-level timestamps.
    Detects timing anomalies and ensures sequential monotonicity.
    """

    @staticmethod
    def refine_word_timestamps(words: List[WordTimestamp]) -> List[WordTimestamp]:
        if not words:
            return []

        refined: List[WordTimestamp] = []
        last_end = 0.0

        for w in words:
            start = max(last_end, w.start)
            end = max(start + 0.05, w.end)

            # Cap unrealistically long single-word durations (e.g. trailing hallucinations)
            if (end - start) > 4.0:
                logger.debug(f"Anomalous word duration detected for '{w.word}': {end - start:.2f}s, clamping to 1.5s")
                end = start + 1.5

            refined.append(
                WordTimestamp(
                    word=w.word,
                    start=round(start, 3),
                    end=round(end, 3),
                    confidence=round(w.confidence, 3),
                    speaker=w.speaker
                )
            )
            last_end = end

        return refined
