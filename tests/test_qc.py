import pytest
from src.models import SubtitleCue, WordTimestamp, VADSegment
from src.qc.hallucination import HallucinationChecker
from src.qc.confidence import ConfidenceChecker
from src.qc.readability import ReadabilityChecker
from src.qc.speaker import SpeakerConsistencyChecker
from src.qc.scorer import QCEngine

def test_hallucination_detection():
    checker = HallucinationChecker(high_risk_threshold=0.35, medium_risk_threshold=0.65)

    # Cue: 10.0s to 14.0s (4 seconds long)
    # Speech is only present from 10.0s to 10.8s (0.8s overlap -> 20% overlap ratio)
    cue = SubtitleCue(index=1, start=10.0, end=14.0, speaker="SPEAKER_00", text="কাল দেখা হবে।")
    vad = [VADSegment(start=10.0, end=10.8)]

    risk, overlap_sec, ratio, flag = checker.evaluate(cue, vad)
    assert risk == "HIGH"
    assert ratio == 0.20
    assert flag is not None
    assert flag.severity == "HIGH"
    assert flag.flag_type == "hallucination"

def test_hallucination_legitimate_speech():
    checker = HallucinationChecker(high_risk_threshold=0.35, medium_risk_threshold=0.65)
    # 90% overlap
    cue = SubtitleCue(index=1, start=2.0, end=4.0, speaker="SPEAKER_00", text="কথা বলছি।")
    vad = [VADSegment(start=2.0, end=3.8)]

    risk, overlap_sec, ratio, flag = checker.evaluate(cue, vad)
    assert risk == "LOW"
    assert ratio == 0.90
    assert flag is None

def test_asr_confidence_flag():
    checker = ConfidenceChecker(low_confidence_threshold=0.60)
    cue = SubtitleCue(
        index=1,
        start=1.0,
        end=2.5,
        speaker="SPEAKER_00",
        text="অস্পষ্ট শব্দ",
        words=[
            WordTimestamp(word="অস্পষ্ট", start=1.0, end=1.7, confidence=0.32),
            WordTimestamp(word="শব্দ", start=1.8, end=2.5, confidence=0.41)
        ]
    )
    conf, flag = checker.evaluate(cue)
    assert conf < 0.45
    assert flag is not None
    assert flag.severity == "HIGH"

def test_cps_readability_violation():
    checker = ReadabilityChecker(max_cps=17.0)
    # 40 characters in 1.0 second = 40 CPS (violates 17 CPS threshold)
    long_text = "এই দীর্ঘ বাক্যটি অত্যন্ত দ্রুত বলা হয়েছে।"
    cue = SubtitleCue(index=1, start=1.0, end=2.0, speaker="SPEAKER_00", text=long_text)
    cps, lines, max_l, risk, flags = checker.evaluate(cue)
    assert cps > 17.0
    assert risk in ("HIGH", "MEDIUM")
    assert any(f.flag_type == "cps_violation" for f in flags)

def test_qc_engine_ranking():
    engine = QCEngine()

    # Cue 1: Low risk (good VAD overlap, high confidence)
    cue1 = SubtitleCue(
        index=1, start=1.0, end=3.0, speaker="SPEAKER_00", text="সুপ্রভাত",
        words=[WordTimestamp(word="সুপ্রভাত", start=1.0, end=3.0, confidence=0.98)]
    )

    # Cue 2: High hallucination risk (no speech overlap)
    cue2 = SubtitleCue(
        index=2, start=10.0, end=14.0, speaker="SPEAKER_00", text="অলীক বাক্য",
        words=[WordTimestamp(word="অলীক", start=10.0, end=12.0, confidence=0.40)]
    )

    vad = [VADSegment(start=1.0, end=3.0)]  # speech only for cue 1
    report = engine.evaluate_cues([cue1, cue2], vad)

    assert report.total_cues == 2
    assert len(report.review_queue) >= 1
    # Highest priority cue in queue should be Cue 2
    assert report.review_queue[0].cue_index == 2
    assert report.review_queue[0].review_priority > report.cues[0].review_priority
