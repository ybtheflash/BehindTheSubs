import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.models import (
    SubtitleCue,
    CueQC,
    PipelineQCReport,
    VADSegment,
    ShotBoundary,
    QCFlag
)
from src.qc.hallucination import HallucinationChecker
from src.qc.confidence import ConfidenceChecker
from src.qc.speaker import SpeakerConsistencyChecker
from src.qc.readability import ReadabilityChecker
from src.qc.timing import TimingChecker
from src.config import default_config

logger = logging.getLogger(__name__)

class QCEngine:
    """
    Central AI Quality Control & Risk Aggregator.
    Evaluates independent signals and creates transparent review priority scores.
    """

    def __init__(self, config=default_config):
        self.config = config
        self.hallucination_checker = HallucinationChecker(
            high_risk_threshold=config.hallucination_high_threshold,
            medium_risk_threshold=config.hallucination_medium_threshold
        )
        self.confidence_checker = ConfidenceChecker(
            low_confidence_threshold=config.asr_confidence_low_threshold
        )
        self.speaker_checker = SpeakerConsistencyChecker()
        self.readability_checker = ReadabilityChecker(
            max_cps=config.max_cps,
            max_lines=config.max_lines,
            max_chars_per_line=config.max_chars_per_line
        )
        self.timing_checker = TimingChecker(
            min_cue_duration=config.min_cue_duration,
            max_cue_duration=config.max_cue_duration
        )

    def evaluate_cues(
        self,
        cues: List[SubtitleCue],
        vad_segments: List[VADSegment],
        shot_boundaries: Optional[List[ShotBoundary]] = None
    ) -> PipelineQCReport:
        if not cues:
            return PipelineQCReport(
                total_cues=0,
                low_risk_count=0,
                medium_risk_count=0,
                high_risk_count=0,
                avg_cps=0.0,
                total_speech_duration=0.0,
                speaker_distribution={},
                cues=[],
                review_queue=[]
            )

        evaluated_cues: List[CueQC] = []
        speaker_counts: Dict[str, int] = {}
        total_cps = 0.0

        for i, cue in enumerate(cues):
            prev_cue = cues[i - 1] if i > 0 else None
            next_cue = cues[i + 1] if i + 1 < len(cues) else None

            # 1. Hallucination check (VAD overlap)
            h_risk, overlap_sec, overlap_ratio, h_flag = self.hallucination_checker.evaluate(
                cue, vad_segments
            )

            # 2. ASR confidence check
            asr_conf, conf_flag = self.confidence_checker.evaluate(cue)

            # 3. Speaker continuity check
            spk_cont, spk_risk, spk_flag = self.speaker_checker.evaluate(cue, prev_cue, next_cue)

            # 4. Readability check (CPS, lines, characters)
            cps, line_count, max_line_len, read_risk, read_flags = self.readability_checker.evaluate(cue)

            # 5. Timing check (duration, shot boundaries)
            shot_conflict, timing_risk, timing_flags = self.timing_checker.evaluate(cue, shot_boundaries)

            # Aggregate flags
            all_flags: List[QCFlag] = []
            if h_flag:
                all_flags.append(h_flag)
            if conf_flag:
                all_flags.append(conf_flag)
            if spk_flag:
                all_flags.append(spk_flag)
            all_flags.extend(read_flags)
            all_flags.extend(timing_flags)

            # Calculate transparent weighted review priority
            # Hallucination (0.40) + Confidence (0.25) + Speaker (0.15) + Readability (0.12) + Timing (0.08)
            h_score = 1.0 - overlap_ratio
            conf_score = 1.0 - asr_conf
            spk_score = 0.8 if spk_risk == "HIGH" else (0.4 if spk_risk == "MEDIUM" else 0.0)
            read_score = 0.8 if read_risk == "HIGH" else (0.4 if read_risk == "MEDIUM" else 0.0)
            timing_score = 0.8 if timing_risk == "HIGH" else (0.4 if timing_risk == "MEDIUM" else 0.0)

            review_priority = (
                0.40 * h_score +
                0.25 * conf_score +
                0.15 * spk_score +
                0.12 * read_score +
                0.08 * timing_score
            )
            review_priority = round(min(1.0, max(0.0, review_priority)), 2)

            cue_qc = CueQC(
                cue_index=cue.index,
                start=cue.start,
                end=cue.end,
                speaker=cue.speaker,
                text=cue.text,
                asr_confidence=asr_conf,
                speech_overlap=overlap_ratio,
                speaker_continuity=spk_cont,
                cps=cps,
                line_count=line_count,
                max_char_per_line=max_line_len,
                shot_boundary_conflict=shot_conflict,
                hallucination_risk=h_risk,
                speaker_risk=spk_risk,
                readability_risk=read_risk,
                timing_risk=timing_risk,
                review_priority=review_priority,
                flags=all_flags,
                translations=cue.translations
            )
            evaluated_cues.append(cue_qc)

            # Accumulate statistics
            spk = cue.speaker or "SPEAKER_00"
            speaker_counts[spk] = speaker_counts.get(spk, 0) + 1
            total_cps += cps

        # Categorize cues
        high_risk_cues = [c for c in evaluated_cues if c.review_priority >= 0.65]
        medium_risk_cues = [c for c in evaluated_cues if 0.35 <= c.review_priority < 0.65]
        low_risk_cues = [c for c in evaluated_cues if c.review_priority < 0.35]

        # Review queue is sorted by review priority descending
        review_queue = sorted(
            [c for c in evaluated_cues if c.review_priority >= 0.35],
            key=lambda x: x.review_priority,
            reverse=True
        )

        total_speech_dur = sum((s.end - s.start) for s in vad_segments)

        report = PipelineQCReport(
            total_cues=len(evaluated_cues),
            low_risk_count=len(low_risk_cues),
            medium_risk_count=len(medium_risk_cues),
            high_risk_count=len(high_risk_cues),
            avg_cps=round(total_cps / len(evaluated_cues), 2) if evaluated_cues else 0.0,
            total_speech_duration=round(total_speech_dur, 2),
            speaker_distribution=speaker_counts,
            cues=evaluated_cues,
            review_queue=review_queue
        )

        logger.info(
            f"QC Complete: {len(evaluated_cues)} total cues -> "
            f"{len(low_risk_cues)} Low Risk, {len(medium_risk_cues)} Review Recommended, "
            f"{len(high_risk_cues)} High Risk."
        )
        return report

def export_qc_json(report: PipelineQCReport, output_path: str) -> str:
    """
    Exports full machine-readable QC report to JSON.
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
    return str(out_p)

def export_qc_html(report: PipelineQCReport, output_path: str) -> str:
    """
    Exports beautiful, interactive, human-readable QC report to HTML.
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    rows_html = []
    for cue in report.cues:
        priority_pct = int(cue.review_priority * 100)
        if cue.review_priority >= 0.65:
            badge_class = "badge-high"
            status_text = "HIGH RISK"
        elif cue.review_priority >= 0.35:
            badge_class = "badge-med"
            status_text = "REVIEW"
        else:
            badge_class = "badge-low"
            status_text = "LOW RISK"

        flags_text = "<br>".join([f"• <b>{f.severity}:</b> {f.message}" for f in cue.flags]) or "<i>No issues flagged</i>"

        rows_html.append(f"""
        <tr class="{badge_class}-row">
            <td><b>#{cue.cue_index}</b></td>
            <td><code>{cue.start:.2f}s - {cue.end:.2f}s</code></td>
            <td><span class="spk-tag">{cue.speaker}</span></td>
            <td>{cue.text}</td>
            <td><span class="badge {badge_class}">{status_text} ({priority_pct}%)</span></td>
            <td>{cue.speech_overlap * 100:.0f}%</td>
            <td>{cue.asr_confidence * 100:.0f}%</td>
            <td>{cue.cps}</td>
            <td class="flags-cell">{flags_text}</td>
        </tr>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bong2Subs — Automated QC Report</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --border: #334155;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --accent: #38bdf8;
            --high: #ef4444;
            --med: #f59e0b;
            --low: #10b981;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 32px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}
        h1 {{ margin: 0; font-size: 28px; color: var(--accent); }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 36px;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }}
        .card-val {{
            font-size: 32px;
            font-weight: 700;
            margin-top: 8px;
        }}
        .c-high {{ color: var(--high); }}
        .c-med {{ color: var(--med); }}
        .c-low {{ color: var(--low); }}
        .c-acc {{ color: var(--accent); }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--surface);
            border-radius: 12px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        th {{ background: #162032; color: var(--text-dim); text-transform: uppercase; font-size: 12px; letter-spacing: 0.05em; }}
        .spk-tag {{
            background: #2563eb33;
            color: #60a5fa;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            display: inline-block;
        }}
        .badge-high {{ background: #ef444422; color: var(--high); border: 1px solid #ef444466; }}
        .badge-med {{ background: #f59e0b22; color: var(--med); border: 1px solid #f59e0b66; }}
        .badge-low {{ background: #10b98122; color: var(--low); border: 1px solid #10b98166; }}
        .flags-cell {{ font-size: 12px; line-height: 1.4; color: var(--text-dim); }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Bong2Subs — Localisation Quality Control Report</h1>
            <p style="color: var(--text-dim); margin-top: 6px;">AI-Native Subtitle Verification & Risk Priority Assessment</p>
        </div>
        <div style="text-align: right; color: var(--text-dim); font-size: 13px;">
            Generated by Bong2Subs QC Engine
        </div>
    </div>

    <div class="metrics-grid">
        <div class="card">
            <div style="color: var(--text-dim);">Total Cues</div>
            <div class="card-val c-acc">{report.total_cues}</div>
        </div>
        <div class="card">
            <div style="color: var(--text-dim);">High Risk (Action Needed)</div>
            <div class="card-val c-high">{report.high_risk_count}</div>
        </div>
        <div class="card">
            <div style="color: var(--text-dim);">Review Recommended</div>
            <div class="card-val c-med">{report.medium_risk_count}</div>
        </div>
        <div class="card">
            <div style="color: var(--text-dim);">Low Risk (Auto-Accepted)</div>
            <div class="card-val c-low">{report.low_risk_count}</div>
        </div>
        <div class="card">
            <div style="color: var(--text-dim);">Average Reading Speed</div>
            <div class="card-val">{report.avg_cps} <span style="font-size: 16px; font-weight: normal; color: var(--text-dim);">CPS</span></div>
        </div>
    </div>

    <h2 style="margin-bottom: 16px;">Detailed Cue Inspection</h2>
    <table>
        <thead>
            <tr>
                <th>Cue</th>
                <th>Time Range</th>
                <th>Speaker</th>
                <th>Bengali Text</th>
                <th>Review Priority</th>
                <th>Speech Overlap</th>
                <th>ASR Conf</th>
                <th>CPS</th>
                <th>Risk Evidence & Flags</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows_html)}
        </tbody>
    </table>
</body>
</html>
"""
    with open(out_p, "w", encoding="utf-8") as f:
        f.write(html_content)
    return str(out_p)
