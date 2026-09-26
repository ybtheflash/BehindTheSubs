import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

import json
import logging
import argparse
from typing import Optional, Callable, Dict, Any, List

from src.models import (
    WordTimestamp,
    SubtitleCue,
    VADSegment,
    SpeakerSegment,
    ShotBoundary,
    PipelineResult,
    PipelineQCReport
)
from src.config import default_config, PipelineConfig
from src.audio import extract_audio, get_audio_info
from src.vad import VADDetector
from src.shot_detect import ShotBoundaryDetector
from src.asr import BengaliASREngine
from src.alignment import WordAlignmentProcessor
from src.diarize import SpeakerDiarizer
from src.speaker_merge import SpeakerWordReconciler
from src.cue_segmenter import SubtitleCueSegmenter
from src.translate import SubtitleTranslator
from src.formats.vtt_writer import write_vtt
from src.formats.srt_writer import write_srt
from src.qc.scorer import QCEngine, export_qc_json, export_qc_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Bong2Subs.Pipeline")

class Bong2SubsPipeline:
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or default_config
        self.vad_detector = VADDetector()
        self.shot_detector = ShotBoundaryDetector()
        self.asr_engine = BengaliASREngine(
            default_provider=self.config.asr_provider,
            model_size=self.config.asr_model,
            device=self.config.asr_device,
            compute_type=self.config.asr_compute_type,
            language=self.config.asr_language
        )
        self.diarizer = SpeakerDiarizer(
            model_name=self.config.diarization_model,
            hf_token=self.config.hf_token
        )
        self.cue_segmenter = SubtitleCueSegmenter(
            max_cps=self.config.max_cps,
            max_lines=self.config.max_lines,
            max_chars_per_line=self.config.max_chars_per_line,
            min_cue_duration=self.config.min_cue_duration,
            max_cue_duration=self.config.max_cue_duration
        )
        self.translator = SubtitleTranslator(
            anthropic_key=self.config.anthropic_api_key,
            openai_key=self.config.openai_api_key,
            gemini_key=self.config.gemini_api_key
        )
        self.qc_engine = QCEngine(config=self.config)

    def run(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        target_languages: List[str] = ("en", "hi"),
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        use_cache: bool = True,
        asr_provider: Optional[str] = None,
        asr_api_key: Optional[str] = None,
        gemini_key: Optional[str] = None
    ) -> PipelineResult:
        """
        Executes the end-to-end Bong2Subs pipeline:
        Video -> Audio -> VAD + Shots -> ASR -> Alignment -> Diarization ->
        Merge -> Cue Segmentation -> Translation -> QC Engine -> Reports & Subtitle Files.
        """
        video_p = Path(video_path).resolve()
        if not video_p.exists():
            raise FileNotFoundError(f"Input file not found: {video_path}")

        out_dir = Path(output_dir or self.config.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        art_dir = self.config.artifacts_dir / video_p.stem
        art_dir.mkdir(parents=True, exist_ok=True)

        def emit_progress(stage: str, percent: int, msg: str):
            logger.info(f"[{percent}%] [{stage}] {msg}")
            if progress_callback:
                try:
                    progress_callback(stage, percent, msg)
                except Exception as e:
                    logger.warning(f"Error in progress callback: {e}")

        # Stage 1: Audio Extraction
        emit_progress("audio", 10, "Extracting audio with FFmpeg...")
        audio_path = str(art_dir / "audio.wav")
        if not (use_cache and Path(audio_path).exists()):
            extract_audio(str(video_p), audio_path)
        audio_info = get_audio_info(audio_path)
        emit_progress("audio", 15, f"Audio ready: {audio_info.get('duration', 0):.1f}s duration.")

        # Stage 2: VAD & Speech Boundary Detection
        emit_progress("vad", 25, "Running Silero VAD speech detection...")
        vad_cache_path = art_dir / "vad.json"
        if use_cache and vad_cache_path.exists():
            with open(vad_cache_path, "r", encoding="utf-8") as f:
                vad_data = json.load(f)
                vad_segments = [VADSegment(**d) for d in vad_data]
        else:
            vad_segments = self.vad_detector.detect_speech(audio_path)
            with open(vad_cache_path, "w", encoding="utf-8") as f:
                json.dump([s.to_dict() for s in vad_segments], f, indent=2)

        # Stage 3: Shot Detection
        emit_progress("shot", 30, "Detecting video scene/shot boundaries...")
        shot_boundaries = self.shot_detector.detect_shots(str(video_p))

        # Stage 4: Bengali ASR & Word Timestamps (Provider-Aware Caching)
        emit_progress("asr", 45, f"Running Bengali ASR transcription with provider: {asr_provider or self.config.asr_provider}...")
        
        req_provider = (asr_provider or self.config.asr_provider or "bengali_whisper").lower()
        if "gemini" in req_provider:
            norm_provider = "gemini"
        elif "xlsr" in req_provider or "bengali-asr" in req_provider:
            norm_provider = "bengali_xlsr"
        elif "whisper.cpp" in req_provider or "faster-whisper" in req_provider:
            norm_provider = "whisper"
        elif any(k in req_provider for k in ("whisper", "bengali", "ybtheflash", "tugstugi")):
            norm_provider = "bengali_whisper"
        elif "mimo" in req_provider:
            norm_provider = "mimo"
        else:
            norm_provider = "bengali_whisper"

        asr_cache_path = art_dir / f"asr_{norm_provider}.json"
        words: List[WordTimestamp] = []
        raw_segments: List[Dict[str, Any]] = []
        loaded_from_cache = False
        used_provider = norm_provider

        # Clean legacy unpartitioned asr.json to prevent stale hits
        legacy_asr_path = art_dir / "asr.json"
        if legacy_asr_path.exists():
            try:
                legacy_asr_path.unlink()
            except Exception:
                pass

        if use_cache and asr_cache_path.exists():
            try:
                with open(asr_cache_path, "r", encoding="utf-8") as f:
                    asr_data = json.load(f)
                cached_prov = asr_data.get("provider", norm_provider).lower()
                if norm_provider in cached_prov:
                    words = [WordTimestamp(**d) for d in asr_data["words"]]
                    raw_segments = asr_data.get("segments", [])
                    loaded_from_cache = True
                    used_provider = cached_prov
                    emit_progress("asr", 48, f"ASR loaded from cache for '{cached_prov}'. Transcribed {len(words)} words.")
            except Exception as e:
                logger.warning(f"Failed to read ASR cache from {asr_cache_path}: {e}")

        if not loaded_from_cache:
            words, raw_segments, used_provider = self.asr_engine.transcribe(
                audio_path,
                provider=asr_provider,
                mimo_key=asr_api_key,
                gemini_key=gemini_key or asr_api_key,
                word_timestamps=True
            )
            emit_progress("asr", 48, f"ASR completed via '{used_provider}'. Transcribed {len(words)} words.")
            with open(asr_cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "provider": used_provider,
                    "words": [w.to_dict() for w in words],
                    "segments": raw_segments
                }, f, ensure_ascii=False, indent=2)

        # Stage 5: Alignment Refinement
        emit_progress("align", 55, "Refining word alignment and temporal monotonicity...")
        words = WordAlignmentProcessor.refine_word_timestamps(words)

        # Stage 6: Speaker Diarization
        emit_progress("diarize", 65, "Performing speaker diarization...")
        diar_cache_path = art_dir / "diarization.json"
        if use_cache and diar_cache_path.exists():
            with open(diar_cache_path, "r", encoding="utf-8") as f:
                diar_data = json.load(f)
                speaker_segments = [SpeakerSegment(**d) for d in diar_data]
        else:
            speaker_segments = self.diarizer.diarize(audio_path, vad_segments)
            with open(diar_cache_path, "w", encoding="utf-8") as f:
                json.dump([s.to_dict() for s in speaker_segments], f, indent=2)

        # Stage 7: Speaker ↔ Word Reconciliation
        emit_progress("merge", 70, "Reconciling speaker attribution with words...")
        words = SpeakerWordReconciler.reconcile(words, speaker_segments)

        # Stage 8: Subtitle Cue Segmentation
        emit_progress("cues", 75, "Generating subtitle cues (CPS, line limits, shot awareness)...")
        cues = self.cue_segmenter.segment(words, shot_boundaries)

        # Stage 9: Translation to English, Hindi, and Romanized tracks
        all_targets = list(target_languages or ["en", "hi"])
        for req_track in ("bn_rom", "hi_rom", "hi", "en"):
            if req_track not in all_targets:
                all_targets.append(req_track)

        emit_progress("translate", 85, f"Translating & transliterating cues into {all_targets}...")
        cues = self.translator.translate_cues(cues, target_languages=all_targets)

        # Save merged cues
        with open(art_dir / "cues.json", "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in cues], f, ensure_ascii=False, indent=2)

        # Stage 10: AI QC Engine & Hallucination Assessment
        emit_progress("qc", 92, "Running AI QC Engine and ranking suspicious cues...")
        qc_report = self.qc_engine.evaluate_cues(cues, vad_segments, shot_boundaries)

        # Stage 11: Export Subtitles & QC Reports
        emit_progress("export", 97, "Writing WebVTT, SRT subtitles and QC reports...")
        vtt_path = str(out_dir / "bn_captions.vtt")
        srt_en_path = str(out_dir / "en_subtitles.srt")
        srt_hi_path = str(out_dir / "hi_subtitles.srt")
        srt_bn_rom_path = str(out_dir / "bn_rom_subtitles.srt")
        srt_hi_rom_path = str(out_dir / "hi_rom_subtitles.srt")
        qc_json_path = str(out_dir / "qc_report.json")
        qc_html_path = str(out_dir / "qc_report.html")

        write_vtt(cues, vtt_path, include_speaker=True)
        write_srt(cues, srt_en_path, language_key="en")
        write_srt(cues, srt_hi_path, language_key="hi")
        write_srt(cues, srt_bn_rom_path, language_key="bn_rom")
        write_srt(cues, srt_hi_rom_path, language_key="hi_rom")
        export_qc_json(qc_report, qc_json_path)
        export_qc_html(qc_report, qc_html_path)

        emit_progress("complete", 100, "Pipeline completed successfully!")

        from datetime import datetime
        return PipelineResult(
            video_path=str(video_p),
            audio_path=audio_path,
            language=self.config.asr_language,
            cues=cues,
            qc_report=qc_report,
            vtt_path=vtt_path,
            srt_en_path=srt_en_path,
            srt_hi_path=srt_hi_path,
            srt_bn_rom_path=srt_bn_rom_path,
            srt_hi_rom_path=srt_hi_rom_path,
            qc_json_path=qc_json_path,
            qc_html_path=qc_html_path,
            asr_provider=used_provider,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

def main():
    parser = argparse.ArgumentParser(description="Bong2Subs — Bengali Subtitle & Closed-Caption Pipeline")
    parser.add_argument("--input", "-i", required=True, help="Path to input Bengali video or audio file")
    parser.add_argument("--output", "-o", default="outputs", help="Output directory")
    parser.add_argument("--lang", default="bn", help="Primary source language")
    parser.add_argument("--translate", nargs="+", default=["en", "hi"], help="Target translation languages")
    parser.add_argument("--no-cache", action="store_true", help="Disable intermediate artifact caching")
    parser.add_argument("--asr-provider", choices=["mimo", "gemini", "whisper.cpp", "whisper", "faster-whisper"], default=None, help="ASR engine: mimo, gemini (gemini-flash-latest), or whisper.cpp (whisper.cpp-1.9.4)")
    parser.add_argument("--mimo-key", default=None, help="Explicit Xiaomi MiMo API key override")
    parser.add_argument("--gemini-key", default=None, help="Explicit Google Gemini API key override")

    args = parser.parse_args()

    pipeline = Bong2SubsPipeline()
    result = pipeline.run(
        video_path=args.input,
        output_dir=args.output,
        target_languages=args.translate,
        use_cache=not args.no_cache,
        asr_provider=args.asr_provider,
        asr_api_key=args.gemini_key if args.asr_provider == "gemini" else args.mimo_key,
        gemini_key=args.gemini_key
    )

    print("\n" + "=" * 60)
    print("[OK] Bong2Subs Pipeline Finished Successfully!")
    print("=" * 60)
    print(f"Total Cues Generated : {result.qc_report.total_cues}")
    print(f"Low Risk (Approved)  : {result.qc_report.low_risk_count}")
    print(f"Review Recommended   : {result.qc_report.medium_risk_count}")
    print(f"High Risk Flags      : {result.qc_report.high_risk_count}")
    print("-" * 60)
    print(f"Bengali WebVTT       : {result.vtt_path}")
    print(f"English Subtitles    : {result.srt_en_path}")
    print(f"Hindi Subtitles      : {result.srt_hi_path}")
    print(f"QC JSON Report       : {result.qc_json_path}")
    print(f"QC HTML Dashboard    : {result.qc_html_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
