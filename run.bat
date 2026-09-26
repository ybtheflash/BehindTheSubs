@echo off
echo =======================================================
echo          Starting Bong2Subs Subtitle Studio
echo =======================================================
echo Serving on http://localhost:8000
python -m uvicorn src.server:app --host 127.0.0.1 --port 8000
pause
