import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

import json
import uuid
import shutil
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from src.pipeline import Bong2SubsPipeline
from src.config import default_config
from src.models import SubtitleCue
from src.formats.vtt_writer import write_vtt
from src.formats.srt_writer import write_srt
from src.qc.scorer import export_qc_json, export_qc_html

logger = logging.getLogger("Bong2Subs.Server")

app = FastAPI(
    title="Bong2Subs API",
    description="Bengali Subtitle & Closed-Caption Pipeline with Speaker Diarization and AI QC Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = default_config.root_dir / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR = default_config.root_dir / "samples"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory pipeline state
PIPELINE_TASKS: Dict[str, Dict[str, Any]] = {}
LATEST_RESULT: Optional[Dict[str, Any]] = None
CURRENT_VIDEO_PATH: Optional[str] = None

class RunPipelineRequest(BaseModel):
    video_path: Optional[str] = None
    target_languages: list[str] = ["en", "hi"]
    use_cache: bool = True
    asr_provider: Optional[str] = None # 'mimo', 'gemini', or 'faster-whisper'
    asr_api_key: Optional[str] = None  # user selected or entered MiMo/Gemini API key
    gemini_key: Optional[str] = None   # explicit Gemini API key override

class UpdateCueRequest(BaseModel):
    cue_index: int
    text: Optional[str] = None
    speaker: Optional[str] = None
    translation_en: Optional[str] = None
    translation_hi: Optional[str] = None
    action: Optional[str] = None  # 'accept', 'reject', 'edited'

@app.get("/api/health/ai")
def ai_health_status():
    """
    Checks if Modal GPU endpoints are awake or sleeping (cold start).
    Returns real-time status and estimated wake-up time.
    """
    import urllib.request
    import time
    from src.bengali_ai_asr import BengaliAIASREngine

    results = {
        "status": "awake",
        "modal_xlsr": {
            "status": "unknown",
            "latency_ms": None,
            "url": BengaliAIASREngine.MODAL_XLSR_URL
        },
        "modal_whisper": {
            "status": "unknown",
            "latency_ms": None,
            "url": BengaliAIASREngine.MODAL_WHISPER_URL
        },
        "estimated_wakeup_seconds": 0,
        "message": "AI Models Awake & Ready on GPU"
    }

    endpoints = [
        ("modal_xlsr", f"{BengaliAIASREngine.MODAL_XLSR_URL}/health"),
        ("modal_whisper", f"{BengaliAIASREngine.MODAL_WHISPER_URL}/health")
    ]

    sleeping_count = 0

    for key, url in endpoints:
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "B2S-HealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                elapsed_ms = int((time.time() - t0) * 1000)
                if resp.status == 200:
                    results[key]["status"] = "awake"
                    results[key]["latency_ms"] = elapsed_ms
                else:
                    results[key]["status"] = "sleeping"
                    results[key]["latency_ms"] = elapsed_ms
                    sleeping_count += 1
        except Exception:
            elapsed_ms = int((time.time() - t0) * 1000)
            results[key]["status"] = "sleeping"
            results[key]["latency_ms"] = elapsed_ms
            sleeping_count += 1

    if sleeping_count > 0:
        results["status"] = "sleeping"
        results["estimated_wakeup_seconds"] = 35
        results["message"] = "AI Server Waking Up (~20-40s cold start on free tier)..."
    else:
        results["status"] = "awake"
        results["estimated_wakeup_seconds"] = 0
        results["message"] = "All AI GPU Endpoints Awake & Ready"

    return results

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Bong2Subs",
        "asr_provider": default_config.asr_provider,
        "bengali_xlsr_available": True,
        "bengali_xlsr_model": "ybtheflash/bengali-asr (XLS-R 300M)",
        "bengali_whisper_available": True,
        "bengali_whisper_model": "ybtheflash/regional_bengali-asr_tugstugi_whisper-medium",
        "mimo_translation_configured": bool(default_config.get_mimo_keys()),
        "mimo_configured": bool(default_config.get_mimo_keys()),
        "mimo_key_count": len(default_config.get_mimo_keys()),
        "gemini_configured": bool(default_config.get_gemini_keys()),
        "gemini_key_count": len(default_config.get_gemini_keys()),
        "gemini_model": default_config.gemini_model,
        "whisper_cpp_available": True,
        "whisper_cpp_version": "1.9.4",
        "asr_device": "CPU (AVX2)",
        "asr_model": f"whisper.cpp ({default_config.whisper_cpp_model})",
        "hf_token_configured": bool(default_config.hf_token),
        "anthropic_configured": bool(default_config.anthropic_api_key),
        "openai_configured": bool(default_config.openai_api_key)
    }

@app.get("/api/config/asr")
def get_asr_config():
    """
    Returns available ASR providers and configured API keys for user switching in the UI panel.
    """
    return {
        "default_provider": default_config.asr_provider,
        "bengali_xlsr_available": True,
        "bengali_xlsr_model": "ybtheflash/bengali-asr (XLS-R 300M)",
        "bengali_whisper_available": True,
        "bengali_whisper_model": "ybtheflash/regional_bengali-asr_tugstugi_whisper-medium",
        "mimo_translation_configured": bool(default_config.get_mimo_keys()),
        "mimo_configured": bool(default_config.get_mimo_keys()),
        "mimo_keys": default_config.get_masked_mimo_keys(),
        "mimo_model": default_config.mimo_model,
        "mimo_base_url": default_config.mimo_base_url,
        "gemini_configured": bool(default_config.get_gemini_keys()),
        "gemini_keys": default_config.get_masked_gemini_keys(),
        "gemini_model": default_config.gemini_model,
        "whisper_cpp_available": True,
        "whisper_cpp_version": "1.9.4",
        "whisper_model": f"ggml-{default_config.whisper_cpp_model}",
        "whisper_device": "CPU (AVX2)"
    }

@app.get("/api/samples")
def get_samples():
    samples = []
    for ext in ("*.mp4", "*.mkv", "*.mov", "*.wav", "*.mp3"):
        for file in SAMPLE_DIR.glob(ext):
            samples.append({
                "name": file.name,
                "path": str(file.resolve()),
                "size_mb": round(file.stat().st_size / (1024 * 1024), 2)
            })
    return {"samples": samples}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    global CURRENT_VIDEO_PATH
    try:
        suffix = Path(file.filename).suffix or ".mp4"
        file_id = f"video_{uuid.uuid4().hex[:8]}{suffix}"
        target_path = UPLOAD_DIR / file_id

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        CURRENT_VIDEO_PATH = str(target_path)
        return {
            "success": True,
            "filename": file.filename,
            "saved_path": CURRENT_VIDEO_PATH,
            "size_bytes": target_path.stat().st_size
        }
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def run_pipeline_worker(
    task_id: str,
    video_path: str,
    target_languages: list[str],
    use_cache: bool,
    asr_provider: Optional[str] = None,
    asr_api_key: Optional[str] = None,
    gemini_key: Optional[str] = None
):
    global LATEST_RESULT, CURRENT_VIDEO_PATH
    CURRENT_VIDEO_PATH = video_path

    def progress_callback(stage: str, percent: int, msg: str):
        PIPELINE_TASKS[task_id]["stage"] = stage
        PIPELINE_TASKS[task_id]["percent"] = percent
        PIPELINE_TASKS[task_id]["logs"].append(f"[{percent}%] [{stage.upper()}] {msg}")

    try:
        LATEST_RESULT = None
        PIPELINE_TASKS[task_id]["status"] = "processing"
        pipeline = Bong2SubsPipeline()
        result = pipeline.run(
            video_path=video_path,
            target_languages=target_languages,
            progress_callback=progress_callback,
            use_cache=use_cache,
            asr_provider=asr_provider,
            asr_api_key=asr_api_key,
            gemini_key=gemini_key or (asr_api_key if asr_provider in ("gemini", "gemini-flash-latest") else None)
        )
        result_dict = result.to_dict()
        LATEST_RESULT = result_dict
        PIPELINE_TASKS[task_id]["status"] = "completed"
        PIPELINE_TASKS[task_id]["result"] = result_dict
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        PIPELINE_TASKS[task_id]["status"] = "failed"
        PIPELINE_TASKS[task_id]["error"] = str(e)
        PIPELINE_TASKS[task_id]["logs"].append(f"ERROR: {str(e)}")

@app.post("/api/pipeline/start")
def start_pipeline(req: RunPipelineRequest, background_tasks: BackgroundTasks):
    video_path = req.video_path or CURRENT_VIDEO_PATH
    if not video_path or not Path(video_path).exists():
        raise HTTPException(status_code=400, detail="No video file provided or file does not exist.")

    task_id = str(uuid.uuid4())[:8]
    PIPELINE_TASKS[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "percent": 0,
        "stage": "init",
        "logs": [f"Pipeline queued (ASR provider: {req.asr_provider or default_config.asr_provider})."],
        "video_path": video_path
    }

    background_tasks.add_task(
        run_pipeline_worker,
        task_id,
        video_path,
        req.target_languages,
        req.use_cache,
        req.asr_provider,
        req.asr_api_key,
        req.gemini_key
    )

    return {"task_id": task_id, "status": "started"}

@app.get("/api/pipeline/status/{task_id}")
def get_pipeline_status(task_id: str):
    if task_id not in PIPELINE_TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return PIPELINE_TASKS[task_id]

@app.get("/api/results")
def get_results():
    if LATEST_RESULT is None:
        return {"result": None, "cues": []}
    return LATEST_RESULT

@app.post("/api/cue/update")
def update_cue(update: UpdateCueRequest):
    global LATEST_RESULT
    if LATEST_RESULT is None:
        raise HTTPException(status_code=404, detail="No pipeline result available.")

    # Find matching cue in results
    cues = LATEST_RESULT.get("cues", [])
    found = False
    for c in cues:
        if c.get("index") == update.cue_index:
            if update.text is not None:
                c["text"] = update.text
            if update.speaker is not None:
                c["speaker"] = update.speaker
            if update.translation_en is not None:
                c.setdefault("translations", {})["en"] = update.translation_en
            if update.translation_hi is not None:
                c.setdefault("translations", {})["hi"] = update.translation_hi
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Cue not found.")

    # Also update in review_queue and qc_report
    qc_report = LATEST_RESULT.get("qc_report", {})
    for qc_c in qc_report.get("cues", []):
        if qc_c.get("cue_index") == update.cue_index:
            if update.text is not None:
                qc_c["text"] = update.text
            if update.speaker is not None:
                qc_c["speaker"] = update.speaker
            if update.action == "accept":
                qc_c["review_priority"] = 0.1
                qc_c["hallucination_risk"] = "LOW"
            break

    # Re-filter review queue
    review_q = [
        c for c in qc_report.get("cues", [])
        if c.get("review_priority", 0) >= 0.35
    ]
    qc_report["review_queue"] = review_q

    # Update exported files
    try:
        models = [SubtitleCue(**c) for c in cues]
        if LATEST_RESULT.get("vtt_path"):
            write_vtt(models, LATEST_RESULT["vtt_path"])
        if LATEST_RESULT.get("srt_en_path"):
            write_srt(models, LATEST_RESULT["srt_en_path"], language_key="en")
        if LATEST_RESULT.get("srt_hi_path"):
            write_srt(models, LATEST_RESULT["srt_hi_path"], language_key="hi")
        if LATEST_RESULT.get("srt_bn_rom_path"):
            write_srt(models, LATEST_RESULT["srt_bn_rom_path"], language_key="bn_rom")
        if LATEST_RESULT.get("srt_hi_rom_path"):
            write_srt(models, LATEST_RESULT["srt_hi_rom_path"], language_key="hi_rom")
    except Exception as e:
        logger.warning(f"Failed to refresh subtitle exports after update: {e}")

    return {"success": True, "updated_cue_index": update.cue_index}

@app.get("/api/video")
def stream_video(video_path: Optional[str] = None):
    target = video_path or CURRENT_VIDEO_PATH
    if not target or not Path(target).exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(target, media_type="video/mp4")

@app.get("/api/export/{file_type}")
def export_file(file_type: str):
    if LATEST_RESULT is None:
        raise HTTPException(status_code=404, detail="No active result")

    if file_type in ("bundle", "zip"):
        import zipfile
        zip_path = default_config.temp_dir / "bong2subs_deliverables.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for key, name in [
                ("vtt_path", "bn_captions.vtt"),
                ("srt_hi_path", "hi_subtitles.srt"),
                ("srt_bn_rom_path", "bn_rom_subtitles.srt"),
                ("srt_hi_rom_path", "hi_rom_subtitles.srt"),
                ("srt_en_path", "en_subtitles.srt"),
                ("qc_json_path", "qc_report.json"),
                ("qc_html_path", "qc_report.html")
            ]:
                f = LATEST_RESULT.get(key)
                if f and Path(f).exists():
                    zipf.write(f, arcname=name)
        return FileResponse(str(zip_path), filename="bong2subs_deliverables.zip", media_type="application/zip")

    mapping = {
        "vtt": (LATEST_RESULT.get("vtt_path"), "bn_captions.vtt", "text/vtt"),
        "srt_en": (LATEST_RESULT.get("srt_en_path"), "en_subtitles.srt", "text/plain"),
        "srt_hi": (LATEST_RESULT.get("srt_hi_path"), "hi_subtitles.srt", "text/plain"),
        "srt_bn_rom": (LATEST_RESULT.get("srt_bn_rom_path"), "bn_rom_subtitles.srt", "text/plain"),
        "srt_hi_rom": (LATEST_RESULT.get("srt_hi_rom_path"), "hi_rom_subtitles.srt", "text/plain"),
        "qc_json": (LATEST_RESULT.get("qc_json_path"), "qc_report.json", "application/json"),
        "qc_html": (LATEST_RESULT.get("qc_html_path"), "qc_report.html", "text/html"),
    }

    if file_type not in mapping:
        raise HTTPException(status_code=400, detail="Invalid export file type")

    fpath, filename, media_type = mapping[file_type]
    if not fpath or not Path(fpath).exists():
        raise HTTPException(status_code=404, detail="Export file missing")

    return FileResponse(fpath, filename=filename, media_type=media_type)

@app.post("/api/clear")
@app.delete("/api/clear")
def clear_all_backend_data():
    """
    Completely purges all backend data, pipeline artifacts, outputs,
    uploaded media files, temporary files, and resets in-memory pipeline state.
    """
    global PIPELINE_TASKS, LATEST_RESULT, CURRENT_VIDEO_PATH
    task_count = len(PIPELINE_TASKS)
    PIPELINE_TASKS.clear()
    LATEST_RESULT = None
    CURRENT_VIDEO_PATH = None

    purged_dirs = []
    target_dirs = [
        default_config.output_dir,
        default_config.artifacts_dir,
        default_config.temp_dir,
        UPLOAD_DIR
    ]

    for d in target_dirs:
        if d.exists():
            for item in d.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Error deleting {item}: {e}")
            purged_dirs.append(d.name)
        else:
            d.mkdir(parents=True, exist_ok=True)

    logger.info("All backend data and in-memory state cleared successfully.")
    return {
        "success": True,
        "message": "All backend data, pipeline artifacts, outputs, and in-memory cache have been completely cleared.",
        "purged_tasks": task_count,
        "purged_directories": purged_dirs
    }

# Mount built frontend static files if available
FRONTEND_DIST = default_config.root_dir / "frontend" / "dist"
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    logger.info(f"Starting Bong2Subs server on http://{host}:{port}")
    uvicorn.run("src.server:app", host=host, port=port, reload=False)

