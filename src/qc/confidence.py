from typing import Tuple, Optional
from src.models import SubtitleCue, QCFlag

class ConfidenceChecker:
    """
    Evaluates acoustic and linguistic ASR confidence at word and cue levels.
    """

    def __init__(self, low_confidence_threshold: float = 0.60):
        self.low_confidence_threshold = low_confidence_threshold

    def evaluate(self, cue: SubtitleCue) -> Tuple[float, Optional[QCFlag]]:
        """
        Calculates average word confidence for the cue.
        Returns:
            - asr_confidence: float (0.0 to 1.0)
            - flag: QCFlag if confidence is noticeably low
        """
        if not cue.words:
            return 0.85, None

        confidences = [w.confidence for w in cue.words if hasattr(w, "confidence")]
        if not confidences:
            return 0.85, None

        avg_conf = round(sum(confidences) / len(confidences), 3)
        min_conf = round(min(confidences), 3)
        low_words = [w.word for w in cue.words if w.confidence < self.low_confidence_threshold]

        flag = None
        if avg_conf < self.low_confidence_threshold:
            flag = QCFlag(
                flag_type="asr_confidence",
                severity="HIGH" if avg_conf < 0.45 else "MEDIUM",
                score=round(1.0 - avg_conf, 2),
                message=f"Low ASR transcription confidence ({int(avg_conf * 100)}%). Low-confidence words: {', '.join(low_words[:4])}",
                evidence={
                    "avg_confidence": avg_conf,
                    "min_confidence": min_conf,
                    "low_confidence_words": low_words
                }
            )
        elif low_words:
            flag = QCFlag(
                flag_type="asr_confidence",
                severity="LOW",
                score=round(1.0 - min_conf, 2),
                message=f"Contains isolated low-confidence words ({len(low_words)}): {', '.join(low_words[:3])}",
                evidence={"low_confidence_words": low_words, "min_confidence": min_conf}
            )

        return avg_conf, flag
