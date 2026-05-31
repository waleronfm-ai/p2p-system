@echo off
chcp 65001 >nul
cd /d "%~dp0"

start "P2P Vite" cmd /k "cd /d %~dp0frontend && npm run dev"
start "P2P Panel" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m http.server 9999"
timeout /t 6 /nobreak >nul
start "" "http://localhost:5173"
start "" "http://localhost:9999/panel.html"
