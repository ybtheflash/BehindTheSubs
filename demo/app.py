import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

import json
import streamlit as st
from src.pipeline import Bong2SubsPipeline
from src.config import default_config

st.set_page_config(
    page_title="Bong2Subs — Bengali Subtitle & QC Pipeline",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main { background-color: #0b0f19; }
    .stButton>button {
        background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
    }
    .badge-high { background: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 4px 10px; border-radius: 12px; font-weight: 700; border: 1px solid rgba(239, 68, 68, 0.4); }
    .badge-med { background: rgba(245, 158, 11, 0.15); color: #f59e0b; padding: 4px 10px; border-radius: 12px; font-weight: 700; border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-low { background: rgba(16, 185, 129, 0.15); color: #10b981; padding: 4px 10px; border-radius: 12px; font-weight: 700; border: 1px solid rgba(16, 185, 129, 0.4); }
    .spk-pill { background: rgba(59, 130, 246, 0.15); color: #60a5fa; padding: 2px 8px; border-radius: 6px; font-family: monospace; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None

if "seek_timestamp" not in st.session_state:
    st.session_state.seek_timestamp = 0.0

st.sidebar.title("🎬 Bong2Subs")
st.sidebar.caption("Bengali Media Localisation & AI QC Engine")

nav = st.sidebar.radio(
    "Navigation",
    ["1. Upload & Run", "2. Review Queue", "3. Video & Subtitles", "4. QC Analytics", "5. Deliverables"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Engine Settings:**")
st.sidebar.text(f"Device: {default_config.asr_device}")
st.sidebar.text(f"ASR Model: {default_config.asr_model}")
st.sidebar.text(f"Diarization: pyannote / clustering")

# 1. Upload & Run
if nav == "1. Upload & Run":
    st.title("Upload Bengali Video Asset")
    st.write("Extract audio, perform speech recognition, speaker attribution, translation and AI hallucination detection.")

    col1, col2 = st.columns([1.2, 0.8])

    with col1:
        uploaded_file = st.file_uploader("Choose a Bengali video file", type=["mp4", "mkv", "mov", "wav"])
        
        sample_path = Path("samples/bengali_sample.mp4")
        use_sample = False
        if sample_path.exists():
            st.write("---")
            use_sample = st.checkbox("Or use pre-packaged benchmark clip (`samples/bengali_sample.mp4`)")

        st.subheader("Speech Recognition (ASR) Engine")
        asr_choice = st.radio(
            "Select ASR Provider",
            [
                "Xiaomi MiMo ASR 2.5 (mimo-v2.5-asr Cloud API)",
                "Google Gemini Flash (gemini-flash-latest Cloud API)",
                "whisper.cpp (whisper.cpp-1.9.4 C++ AVX2)"
            ],
            index=0 if default_config.asr_provider == "mimo" else (1 if default_config.asr_provider == "gemini" else 2)
        )
        if "MiMo" in asr_choice:
            chosen_provider = "mimo"
        elif "Gemini" in asr_choice:
            chosen_provider = "gemini"
        else:
            chosen_provider = "whisper.cpp"

        custom_key = ""
        if chosen_provider == "mimo":
            keys = default_config.get_masked_mimo_keys()
            st.caption(f"Configured MiMo keys in pool: {len(keys)}")
            custom_key = st.text_input("Custom MiMo API Key (optional override):", type="password")
        elif chosen_provider == "gemini":
            keys = default_config.get_masked_gemini_keys()
            st.caption(f"Configured Gemini keys in pool: {len(keys)} (Model: {default_config.gemini_model})")
            custom_key = st.text_input("Custom Google Gemini API Key (optional override):", type="password")

        st.subheader("Pipeline Target Settings")
        translate_en = st.checkbox("Generate English Subtitles (.srt)", value=True)
        translate_hi = st.checkbox("Generate Hindi Subtitles (.srt)", value=True)
        use_cache = st.checkbox("Use intermediate artifact cache", value=True)

        langs = []
        if translate_en: langs.append("en")
        if translate_hi: langs.append("hi")

        if st.button("🚀 Run Bong2Subs Pipeline"):
            video_input = None
            if uploaded_file is not None:
                save_dir = Path("uploads")
                save_dir.mkdir(exist_ok=True)
                target = save_dir / uploaded_file.name
                with open(target, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                video_input = str(target)
            elif use_sample and sample_path.exists():
                video_input = str(sample_path)

            if not video_input:
                st.error("Please upload a file or select the benchmark clip.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_cb(stage, percent, msg):
                    progress_bar.progress(percent)
                    status_text.text(f"[{percent}%] {msg}")

                pipeline = Bong2SubsPipeline()
                try:
                    result = pipeline.run(
                        video_path=video_input,
                        target_languages=langs,
                        progress_callback=progress_cb,
                        use_cache=use_cache,
                        asr_provider=chosen_provider,
                        asr_api_key=custom_key.strip() if custom_key.strip() else None
                    )
                    st.session_state.pipeline_result = result
                    st.success("Pipeline execution completed successfully!")
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")

# 2. Review Queue
elif nav == "2. Review Queue":
    st.title("Ranked Human Review Queue")
    st.write("Identifies suspicious cues prioritized by hallucination probability, low confidence, and timing violations.")

    res = st.session_state.pipeline_result
    if not res:
        st.info("Run the pipeline first in 'Upload & Run'.")
    else:
        queue = res.qc_report.review_queue
        if not queue:
            st.success("All generated cues passed QC checks without high or medium risks.")
        else:
            for cue in queue:
                is_high = cue.review_priority >= 0.65
                badge = f"<span class='{'badge-high' if is_high else 'badge-med'}'>{'HIGH RISK' if is_high else 'REVIEW'} ({int(cue.review_priority * 100)}%)</span>"
                
                with st.expander(f"Cue #{cue.cue_index} | [{cue.speaker}] {cue.start:.2f}s - {cue.end:.2f}s"):
                    st.markdown(f"**Status:** {badge} &nbsp;&nbsp; **Speaker:** `<span class='spk-pill'>{cue.speaker}</span>`", unsafe_allow_html=True)
                    st.markdown(f"### Bengali Dialogue: `{cue.text}`")
                    
                    if cue.translations:
                        c_en, c_hi = st.columns(2)
                        with c_en:
                            st.write(f"**English:** {cue.translations.get('en', 'N/A')}")
                        with c_hi:
                            st.write(f"**Hindi:** {cue.translations.get('hi', 'N/A')}")

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Speech Overlap", f"{int(cue.speech_overlap * 100)}%")
                    m2.metric("ASR Confidence", f"{int(cue.asr_confidence * 100)}%")
                    m3.metric("Reading Speed", f"{cue.cps} CPS")
                    m4.metric("Duration", f"{(cue.end - cue.start):.2f}s")

                    if cue.flags:
                        st.write("**Flagged Evidence:**")
                        for f in cue.flags:
                            st.markdown(f"- **{f.severity}:** {f.message}")

# 3. Video & Subtitles
elif nav == "3. Video & Subtitles":
    st.title("Subtitles & Synchronized Playback")
    res = st.session_state.pipeline_result
    if not res:
        st.info("Run the pipeline first to watch video with generated subtitles.")
    else:
        c1, c2 = st.columns([1.2, 0.8])
        with c1:
            st.video(res.video_path)
            st.write(f"**Bengali WebVTT Path:** `{res.vtt_path}`")
            st.write(f"**English SRT Path:** `{res.srt_en_path}`")
            st.write(f"**Hindi SRT Path:** `{res.srt_hi_path}`")
        with c2:
            st.subheader("Cues Transcript")
            for cue in res.cues:
                st.markdown(f"**#{cue.index} [{cue.speaker}] ({cue.start:.2f}s - {cue.end:.2f}s)**")
                st.markdown(f"> {cue.text}")
                if "en" in cue.translations:
                    st.caption(f"EN: {cue.translations['en']}")

# 4. QC Analytics
elif nav == "4. QC Analytics":
    st.title("QC Analytics & Metrics")
    res = st.session_state.pipeline_result
    if not res:
        st.info("Run the pipeline to inspect QC distribution metrics.")
    else:
        rep = res.qc_report
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Cues", rep.total_cues)
        k2.metric("High Risk", rep.high_risk_count)
        k3.metric("Review Advised", rep.medium_risk_count)
        k4.metric("Low Risk", rep.low_risk_count)
        k5.metric("Avg CPS", rep.avg_cps)

        st.subheader("Speaker Breakdown")
        st.json(rep.speaker_distribution)

# 5. Deliverables
elif nav == "5. Deliverables":
    st.title("Deliverables & Exports")
    res = st.session_state.pipeline_result
    if not res:
        st.info("No deliverables generated yet.")
    else:
        st.success("All deliverables have been compiled and validated.")
        col1, col2 = st.columns(2)

        with col1:
            with open(res.vtt_path, "rb") as f:
                st.download_button("Download Bengali Closed Captions (.vtt)", f, file_name="bn_captions.vtt")
            with open(res.srt_en_path, "rb") as f:
                st.download_button("Download English Subtitles (.srt)", f, file_name="en_subtitles.srt")
            with open(res.srt_hi_path, "rb") as f:
                st.download_button("Download Hindi Subtitles (.srt)", f, file_name="hi_subtitles.srt")

        with col2:
            with open(res.qc_json_path, "rb") as f:
                st.download_button("Download QC Report (JSON)", f, file_name="qc_report.json")
            with open(res.qc_html_path, "rb") as f:
                st.download_button("Download QC Interactive Report (HTML)", f, file_name="qc_report.html")
