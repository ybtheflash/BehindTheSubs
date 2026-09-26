from typing import List, Tuple, Optional
from src.models import SubtitleCue, VADSegment, QCFlag
from src.vad import VADDetector

class HallucinationChecker:
    """
    Evaluates speech overlap ratio using independent VAD signals.
    Hallucinations typically appear over background music or silence with low VAD speech overlap.
    """

    def __init__(self, high_risk_threshold: float = 0.35, medium_risk_threshold: float = 0.65):
        self.high_risk_threshold = high_risk_threshold
        self.medium_risk_threshold = medium_risk_threshold

    def evaluate(
        self,
        cue: SubtitleCue,
        vad_segments: List[VADSegment]
    ) -> Tuple[str, float, float, Optional[QCFlag]]:
        """
        Returns:
            - risk_level: 'LOW', 'MEDIUM', 'HIGH'
            - speech_overlap_seconds: float
            - speech_overlap_ratio: float (0.0 to 1.0)
            - flag: QCFlag if risk is elevated, else None
        """
        overlap_sec, overlap_ratio = VADDetector.compute_overlap_ratio(
            cue.start, cue.end, vad_segments
        )

        flag = None
        if overlap_ratio < self.high_risk_threshold:
            risk_level = "HIGH"
            flag = QCFlag(
                flag_type="hallucination",
                severity="HIGH",
                score=round(1.0 - overlap_ratio, 2),
                message=f"High hallucination risk: only {int(overlap_ratio * 100)}% of cue duration overlaps with detected speech.",
                evidence={
                    "cue_duration": round(cue.duration, 2),
                    "speech_overlap_sec": overlap_sec,
                    "speech_overlap_ratio": overlap_ratio,
                    "threshold_high": self.high_risk_threshold
                }
            )
        elif overlap_ratio < self.medium_risk_threshold:
            risk_level = "MEDIUM"
            flag = QCFlag(
                flag_type="hallucination",
                severity="MEDIUM",
                score=round(1.0 - overlap_ratio, 2),
                message=f"Moderate speech overlap: {int(overlap_ratio * 100)}% speech detected during cue.",
                evidence={
                    "cue_duration": round(cue.duration, 2),
                    "speech_overlap_sec": overlap_sec,
                    "speech_overlap_ratio": overlap_ratio,
                    "threshold_med": self.medium_risk_threshold
                }
            )
        else:
            risk_level = "LOW"

        return risk_level, overlap_sec, overlap_ratio, flag
