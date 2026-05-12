@echo off
start powershell -NoExit -ExecutionPolicy Bypass -Command "cd '%~dp0..'; $env:PYTHONUTF8=1; .\venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"
