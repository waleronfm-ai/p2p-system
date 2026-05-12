@echo off
chcp 65001 >nul
title Market Status - P2P System
cd /d C:\Users\inkvi\p2p-system
call .\venv\Scripts\activate.bat
set PYTHONUTF8=1
cls
echo.
echo  ========================================
echo   Market Status - all pairs summary
echo  ========================================
echo.
python scripts/market.py summary
echo.
echo  ========================================
echo   Intra-exchange spread  - market health
echo   Cross-exchange spread  - arbitrage
echo  ========================================
pause
