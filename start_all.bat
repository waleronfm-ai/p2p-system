@echo off
cd /d "%~dp0"

start "P2P Tracker"  powershell -NoExit -ExecutionPolicy Bypass -Command "& '%~dp0scripts\start_tracker_background.ps1'"
start "P2P API"      powershell -NoExit -ExecutionPolicy Bypass -Command "cd '%~dp0'; $env:PYTHONUTF8=1; .\venv\Scripts\Activate.ps1; .\venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"
start "P2P Frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "cd '%~dp0frontend'; npm run dev"
start "P2P Claude Code" powershell -NoExit -ExecutionPolicy Bypass -Command "cd '%~dp0'; $env:PYTHONUTF8=1; .\venv\Scripts\Activate.ps1"
start "P2P Workspace"   powershell -NoExit -ExecutionPolicy Bypass -Command "cd '%~dp0'; $env:PYTHONUTF8=1; .\venv\Scripts\Activate.ps1"

timeout /t 13 /nobreak

start "" "http://localhost:5173"
start "" "http://localhost:8000/docs"
