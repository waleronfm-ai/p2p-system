$Host.UI.RawUI.WindowTitle = "P2P Tracker - Live"
Set-Location "C:\Users\inkvi\p2p-system"
& ".\venv\Scripts\Activate.ps1"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "C:\Users\inkvi\p2p-system"
Write-Host "============================================" -ForegroundColor Green
Write-Host "  P2P Tracker started" -ForegroundColor Green
Write-Host "  To stop: Ctrl+C" -ForegroundColor Yellow
Write-Host "  To check data in another window:" -ForegroundColor Cyan
Write-Host "    python scripts/check_db.py" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
python scripts/run_tracker.py
