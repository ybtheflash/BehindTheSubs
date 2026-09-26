@echo off
echo Starting Bong2Subs in Live Dev Mode...
start cmd /k "python -m uvicorn src.server:app --reload --port 8000"
start cmd /k "pnpm --dir frontend dev"
