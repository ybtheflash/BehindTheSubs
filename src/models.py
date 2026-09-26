from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float
    confidence: float = 1.0
    speaker: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SpeakerSegment:
    speaker: str
    start: float
    end: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class VADSegment:
    start: float
    end: float
    speech_prob: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ShotBoundary:
    start: float
    end: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SubtitleCue:
    index: int
    start: float
    end: float
    speaker: str
    text: str
    words: List[WordTimestamp] = field(default_factory=list)
    translations: Dict[str, str] = field(default_factory=dict) # e.g. {"en": "...", "hi": "..."}

    @property
    def duration(self) -> float:
        return max(0.001, self.end - self.start)

    @property
    def cps(self) -> float:
        # Characters per second (excluding spaces)
        clean_len = len(self.text.replace(" ", ""))
        return round(clean_len / self.duration, 2)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["duration"] = self.duration
        data["cps"] = self.cps
        return data

@dataclass
class QCFlag:
    flag_type: str  # 'hallucination', 'asr_confidence', 'speaker_mismatch', 'cps_violation', 'line_length', 'shot_crossing', 'timing'
    severity: str   # 'INFO', 'LOW', 'MEDIUM', 'HIGH'
    score: float    # 0.0 to 1.0 risk level
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CueQC:
    cue_index: int
    start: float
    end: float
    speaker: str
    text: str
    asr_confidence: float
    speech_overlap: float           # ratio of cue overlapping with detected speech (0.0 - 1.0)
    speaker_continuity: bool        # true if speaker flow is consistent
    cps: float
    line_count: int
    max_char_per_line: int
    shot_boundary_conflict: bool
    hallucination_risk: str         # 'LOW', 'MEDIUM', 'HIGH'
    speaker_risk: str               # 'LOW', 'MEDIUM', 'HIGH'
    readability_risk: str           # 'LOW', 'MEDIUM', 'HIGH'
    timing_risk: str                # 'LOW', 'MEDIUM', 'HIGH'
    review_priority: float          # 0.0 to 1.0 (1.0 = highest urgency)
    flags: List[QCFlag] = field(default_factory=list)
    translations: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PipelineQCReport:
    total_cues: int
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    avg_cps: float
    total_speech_duration: float
    speaker_distribution: Dict[str, int]
    cues: List[CueQC]
    review_queue: List[CueQC]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PipelineResult:
    video_path: str
    audio_path: str
    language: str
    cues: List[SubtitleCue]
    qc_report: PipelineQCReport
    vtt_path: str
    srt_en_path: str
    srt_hi_path: str
    srt_bn_rom_path: str = ""
    srt_hi_rom_path: str = ""
    qc_json_path: str = ""
    qc_html_path: str = ""
    asr_provider: str = "whisper.cpp"
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
