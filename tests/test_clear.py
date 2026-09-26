import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from src.server import app, UPLOAD_DIR
from src.config import default_config

OUTPUT_DIR = default_config.output_dir
ARTIFACT_DIR = default_config.artifacts_dir
TEMP_DIR = default_config.temp_dir
import src.server as server_mod

client = TestClient(app)

def test_api_clear_endpoint():
    # Create dummy files in the directories
    dummy_out = OUTPUT_DIR / "dummy_test.txt"
    dummy_art_dir = ARTIFACT_DIR / "dummy_video"
    dummy_art_dir.mkdir(parents=True, exist_ok=True)
    dummy_art_file = dummy_art_dir / "asr.json"
    dummy_upload = UPLOAD_DIR / "dummy_video.mp4"
    dummy_temp = TEMP_DIR / "dummy_temp.wav"

    dummy_out.write_text("output content")
    dummy_art_file.write_text("artifact content")
    dummy_upload.write_text("upload content")
    dummy_temp.write_text("temp content")

    # Set mock memory state
    server_mod.LATEST_RESULT = {"mock": "data"}
    server_mod.CURRENT_VIDEO_PATH = str(dummy_upload)
    server_mod.PIPELINE_TASKS["mock_task"] = {"status": "completed"}

    # Call /api/clear
    res = client.post("/api/clear")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["purged_tasks"] >= 1
    assert "outputs" in data["purged_directories"] or "artifacts" in data["purged_directories"]

    # Verify global states are reset
    assert server_mod.LATEST_RESULT is None
    assert server_mod.CURRENT_VIDEO_PATH is None
    assert len(server_mod.PIPELINE_TASKS) == 0

    # Verify files were deleted
    assert not dummy_out.exists()
    assert not dummy_art_file.exists()
    assert not dummy_art_dir.exists()
    assert not dummy_upload.exists()
    assert not dummy_temp.exists()

def test_provider_cache_separation(tmp_path):
    from src.models import WordTimestamp
    from src.pipeline import Bong2SubsPipeline
    import json

    art_dir = tmp_path / "artifacts" / "test_video"
    art_dir.mkdir(parents=True, exist_ok=True)

    # Save mock cache for gemini
    gemini_cache = art_dir / "asr_gemini.json"
    with open(gemini_cache, "w", encoding="utf-8") as f:
        json.dump({
            "provider": "gemini",
            "words": [{"word": "নমস্কার", "start": 0.0, "end": 1.0, "confidence": 0.99}],
            "segments": [{"text": "নমস্কার"}]
        }, f)

    # Save mock cache for mimo
    mimo_cache = art_dir / "asr_mimo.json"
    with open(mimo_cache, "w", encoding="utf-8") as f:
        json.dump({
            "provider": "mimo",
            "words": [{"word": "হ্যালো", "start": 0.0, "end": 1.0, "confidence": 0.98}],
            "segments": [{"text": "হ্যালো"}]
        }, f)

    # Verify files exist distinctly
    assert gemini_cache.exists()
    assert mimo_cache.exists()

    with open(gemini_cache, "r", encoding="utf-8") as f:
        g_data = json.load(f)
        assert g_data["provider"] == "gemini"
        assert g_data["words"][0]["word"] == "নমস্কার"

    with open(mimo_cache, "r", encoding="utf-8") as f:
        m_data = json.load(f)
        assert m_data["provider"] == "mimo"
        assert m_data["words"][0]["word"] == "হ্যালো"
