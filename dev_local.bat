@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ##############################################
echo ##                                          ##
echo ##   !!!  LOCAL DEV MODE  !!!               ##
echo ##   VPS NOT USED — ALL LOCAL               ##
echo ##   API:     localhost:8000                ##
echo ##   DB:      data\p2p.db  (local copy)     ##
echo ##   Tracker: NOT started                   ##
echo ##                                          ##
echo ##############################################
echo.

echo Записываю frontend\.env.local (VITE_API_URL=localhost)...
echo VITE_API_URL=http://localhost:8000> frontend\.env.local

echo Запускаю локальный API...
start "P2P API [LOCAL DEV]" cmd /k "cd /d %~dp0 && set PYTHONUTF8=1 && .\venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

echo Запускаю Vite...
start "P2P Frontend [LOCAL DEV]" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 6 /nobreak >nul
start "" "http://localhost:5173"
