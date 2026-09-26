from typing import List, Tuple, Optional
from src.models import SubtitleCue, QCFlag

class SpeakerConsistencyChecker:
    """
    Evaluates speaker attribution stability and continuity across cues.
    Identifies intra-cue speaker collisions and unstable identity flickering.
    """

    @staticmethod
    def evaluate(
        cue: SubtitleCue,
        prev_cue: Optional[SubtitleCue] = None,
        next_cue: Optional[SubtitleCue] = None
    ) -> Tuple[bool, str, Optional[QCFlag]]:
        """
        Returns:
            - speaker_continuity: bool
            - speaker_risk: 'LOW', 'MEDIUM', 'HIGH'
            - flag: Optional[QCFlag]
        """
        # 1. Intra-cue check: Did words within this cue get assigned different speakers?
        speakers_in_cue = set()
        if cue.words:
            for w in cue.words:
                if w.speaker:
                    speakers_in_cue.add(w.speaker)

        if len(speakers_in_cue) > 1:
            return False, "HIGH", QCFlag(
                flag_type="speaker_mismatch",
                severity="HIGH",
                score=0.80,
                message=f"Intra-cue speaker conflict: multiple speakers detected in single cue ({', '.join(speakers_in_cue)})",
                evidence={"speakers_detected": list(speakers_in_cue)}
            )

        # 2. Inter-cue rapid switching check (e.g. 3 turns under 1.5 seconds)
        if prev_cue and next_cue:
            if (
                cue.speaker != prev_cue.speaker and
                cue.speaker != next_cue.speaker and
                prev_cue.speaker == next_cue.speaker and
                cue.duration < 0.8
            ):
                return False, "MEDIUM", QCFlag(
                    flag_type="speaker_mismatch",
                    severity="MEDIUM",
                    score=0.60,
                    message=f"Rapid speaker flicker: momentary switch to {cue.speaker} between {prev_cue.speaker} turns.",
                    evidence={
                        "current_speaker": cue.speaker,
                        "surrounding_speaker": prev_cue.speaker,
                        "duration": cue.duration
                    }
                )

        return True, "LOW", None
