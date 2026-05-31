@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =============================================
echo   P2P View Production
echo   API:      185.223.57.171:8000  (VPS)
echo   Frontend: localhost:5173
echo =============================================
echo.

echo Удаляю frontend\.env.local (если есть)...
del /q frontend\.env.local 2>nul

echo Запускаю Vite...
start "P2P Frontend [PROD VIEW]" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 4 /nobreak >nul
start "" "http://localhost:5173"
