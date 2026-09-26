import modal
from pathlib import Path

# Define the Modal App
app = modal.App("b2s-behind-the-subs")

# Base Debian image with ffmpeg and required dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "git")
    .pip_install(
        "fastapi>=0.115.0",
        "uvicorn>=0.34.0",
        "python-multipart>=0.0.20",
        "pydantic>=2.10.0",
        "python-dotenv>=1.0.0",
        "requests>=2.32.0",
        "httpx>=0.28.0",
        "soundfile>=0.13.0",
        "numpy>=1.26.0",
        "scipy>=1.14.0",
        "gradio-client>=2.7.0",
        "faster-whisper>=1.0.0",
        "webvtt-py>=0.4.6",
        "srt>=3.5.3"
    )
    .add_local_dir("src", remote_path="/root/src", copy=True)
    .add_local_dir("frontend/dist", remote_path="/root/frontend/dist", copy=True)
    .add_local_file(".env", remote_path="/root/.env", copy=True)
)

@app.function(
    image=image,
    cpu=2.0,
    memory=2048,
    timeout=600,
    scaledown_window=300
)
@modal.asgi_app()
def web():
    import os
    os.chdir("/root")
    from src.server import app as fastapi_app
    return fastapi_app
