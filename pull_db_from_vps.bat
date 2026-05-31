@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =============================================
echo   P2P Pull DB from VPS
echo =============================================
echo.

for /f %%i in ('powershell -command "Get-Date -Format 'yyyy-MM-dd_HHmm'"') do set TIMESTAMP=%%i
set DEST=data\p2p_prod_%TIMESTAMP%.db

echo Скачиваю: /opt/p2p-system/data/p2p.db
echo Сохраняю: %DEST%
echo.

scp -P 56777 -i C:\Users\inkvi\.ssh\id_ed25519 root@185.223.57.171:/opt/p2p-system/data/p2p.db %DEST%

if errorlevel 1 (
    echo.
    echo ОШИБКА: scp не удался.
) else (
    echo.
    echo Готово: %DEST%
    echo Рабочий data\p2p.db НЕ тронут.
)
echo.
pause
