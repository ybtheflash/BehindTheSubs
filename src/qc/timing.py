from typing import List, Tuple, Optional
from src.models import SubtitleCue, ShotBoundary, QCFlag
from src.shot_detect import ShotBoundaryDetector
from src.config import default_config

class TimingChecker:
    """
    Checks subtitle cue timing constraints:
    - Min & max duration limits
    - Visual shot boundary crossing
    - Temporal anomalies and overlaps
    """

    def __init__(
        self,
        min_cue_duration: float = default_config.min_cue_duration,
        max_cue_duration: float = default_config.max_cue_duration
    ):
        self.min_cue_duration = min_cue_duration
        self.max_cue_duration = max_cue_duration

    def evaluate(
        self,
        cue: SubtitleCue,
        shot_boundaries: Optional[List[ShotBoundary]] = None
    ) -> Tuple[bool, str, List[QCFlag]]:
        """
        Returns:
            - shot_boundary_conflict: bool
            - timing_risk: 'LOW', 'MEDIUM', 'HIGH'
            - flags: List[QCFlag]
        """
        flags: List[QCFlag] = []
        is_high = False
        is_medium = False

        duration = cue.duration

        # 1. Minimum duration check
        if duration < 0.6:
            is_high = True
            flags.append(
                QCFlag(
                    flag_type="timing",
                    severity="HIGH",
                    score=0.75,
                    message=f"Sub-second cue flash: duration {duration:.2f}s is below minimum {self.min_cue_duration}s.",
                    evidence={"duration": duration, "min_required": self.min_cue_duration}
                )
            )
        elif duration < self.min_cue_duration:
            is_medium = True
            flags.append(
                QCFlag(
                    flag_type="timing",
                    severity="MEDIUM",
                    score=0.45,
                    message=f"Short cue duration: {duration:.2f}s is slightly under recommended {self.min_cue_duration}s.",
                    evidence={"duration": duration, "min_required": self.min_cue_duration}
                )
            )

        # 2. Maximum duration check
        if duration > self.max_cue_duration + 2.0:
            is_high = True
            flags.append(
                QCFlag(
                    flag_type="timing",
                    severity="HIGH",
                    score=0.70,
                    message=f"Lingering subtitle: duration {duration:.2f}s exceeds maximum {self.max_cue_duration}s.",
                    evidence={"duration": duration, "max_allowed": self.max_cue_duration}
                )
            )
        elif duration > self.max_cue_duration:
            is_medium = True
            flags.append(
                QCFlag(
                    flag_type="timing",
                    severity="MEDIUM",
                    score=0.40,
                    message=f"Long subtitle duration: {duration:.2f}s exceeds guideline {self.max_cue_duration}s.",
                    evidence={"duration": duration, "max_allowed": self.max_cue_duration}
                )
            )

        # 3. Shot boundary crossing
        crosses_shot = False
        if shot_boundaries:
            crosses_shot = ShotBoundaryDetector.crosses_shot_boundary(cue.start, cue.end, shot_boundaries)
            if crosses_shot:
                is_medium = True
                flags.append(
                    QCFlag(
                        flag_type="shot_crossing",
                        severity="MEDIUM",
                        score=0.50,
                        message="Subtitle spans across a camera shot cut, causing visual distraction.",
                        evidence={"cue_start": cue.start, "cue_end": cue.end}
                    )
                )

        if is_high:
            timing_risk = "HIGH"
        elif is_medium:
            timing_risk = "MEDIUM"
        else:
            timing_risk = "LOW"

        return crosses_shot, timing_risk, flags
