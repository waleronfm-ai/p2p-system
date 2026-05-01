$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -like "*run_tracker*"
}
if ($procs) {
    foreach ($p in $procs) {
        Write-Host "Останавливаю PID $($p.ProcessId)..." -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force
    }
    Write-Host "Трекер остановлен" -ForegroundColor Green
} else {
    Write-Host "Активный трекер не найден" -ForegroundColor Yellow
}
