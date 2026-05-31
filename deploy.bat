@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =============================================
echo   P2P Deploy to VPS
echo =============================================
echo.
echo Git status (незакоммиченные изменения):
echo.
git status
echo.
echo ВНИМАНИЕ: незакоммиченные изменения НЕ попадут на VPS.
echo Нажми Enter для продолжения или закрой окно для отмены.
echo.
pause

echo.
echo [1/4] Загружаю deploy_apply.sh на VPS...
scp -P 56777 -i C:\Users\inkvi\.ssh\id_ed25519 scripts\deploy_apply.sh root@185.223.57.171:/opt/p2p-system/scripts/deploy_apply.sh
if errorlevel 1 (
    echo ОШИБКА: не удалось загрузить deploy_apply.sh. Прерываю.
    pause
    exit /b 1
)

echo.
echo [2/4] git push origin main...
git push origin main
if errorlevel 1 (
    echo ОШИБКА: git push не удался. Прерываю.
    pause
    exit /b 1
)

echo.
echo [3-4/4] Применяю на VPS (pull + deps + restart)...
ssh -p 56777 -i C:\Users\inkvi\.ssh\id_ed25519 root@185.223.57.171 "chmod +x /opt/p2p-system/scripts/deploy_apply.sh && bash /opt/p2p-system/scripts/deploy_apply.sh"

echo.
echo =============================================
echo   Deploy завершён
echo =============================================
pause
