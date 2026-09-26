from typing import List, Tuple
from src.models import SubtitleCue, QCFlag
from src.config import default_config

class ReadabilityChecker:
    """
    Validates broadcast subtitle readability guidelines:
    - CPS (Characters Per Second)
    - Line count (Max 2 lines)
    - Characters per line (Max 42 characters)
    """

    def __init__(
        self,
        max_cps: float = default_config.max_cps,
        max_lines: int = default_config.max_lines,
        max_chars_per_line: int = default_config.max_chars_per_line
    ):
        self.max_cps = max_cps
        self.max_lines = max_lines
        self.max_chars_per_line = max_chars_per_line

    def evaluate(self, cue: SubtitleCue) -> Tuple[float, int, int, str, List[QCFlag]]:
        """
        Returns:
            - cps: float
            - line_count: int
            - max_chars_in_a_line: int
            - readability_risk: 'LOW', 'MEDIUM', 'HIGH'
            - flags: List[QCFlag]
        """
        lines = [line.strip() for line in cue.text.split("\n") if line.strip()]
        line_count = len(lines) if lines else 1
        max_line_len = max((len(l) for l in lines), default=0)
        cps = cue.cps

        flags: List[QCFlag] = []
        is_high = False
        is_medium = False

        # 1. CPS Check
        if cps > self.max_cps * 1.3:
            is_high = True
            flags.append(
                QCFlag(
                    flag_type="cps_violation",
                    severity="HIGH",
                    score=0.85,
                    message=f"Severe reading speed violation: {cps:.1f} CPS exceeds {self.max_cps} CPS threshold.",
                    evidence={"cps": cps, "threshold": self.max_cps, "duration": cue.duration}
                )
            )
        elif cps > self.max_cps:
            is_medium = True
            flags.append(
                QCFlag(
                    flag_type="cps_violation",
                    severity="MEDIUM",
                    score=0.55,
                    message=f"High reading speed: {cps:.1f} CPS exceeds {self.max_cps} CPS guideline.",
                    evidence={"cps": cps, "threshold": self.max_cps, "duration": cue.duration}
                )
            )

        # 2. Line Count Check
        if line_count > self.max_lines:
            is_high = True
            flags.append(
                QCFlag(
                    flag_type="line_count",
                    severity="HIGH",
                    score=0.75,
                    message=f"Subtitle exceeds maximum permitted line count ({line_count} lines > {self.max_lines}).",
                    evidence={"line_count": line_count, "max_lines": self.max_lines}
                )
            )

        # 3. Line Length Check
        if max_line_len > self.max_chars_per_line + 8:
            is_medium = True
            flags.append(
                QCFlag(
                    flag_type="line_length",
                    severity="MEDIUM",
                    score=0.60,
                    message=f"Line exceeds length standard: {max_line_len} chars > {self.max_chars_per_line}.",
                    evidence={"max_line_length": max_line_len, "limit": self.max_chars_per_line}
                )
            )

        if is_high:
            readability_risk = "HIGH"
        elif is_medium:
            readability_risk = "MEDIUM"
        else:
            readability_risk = "LOW"

        return cps, line_count, max_line_len, readability_risk, flags
