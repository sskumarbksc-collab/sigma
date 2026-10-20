@echo off
title NSE ALPHA-15 PRO - 80%% Sniper & Upstox Live Terminal
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python -c "import uvicorn" >nul 2>nul
    if %errorlevel%==0 (
        echo Starting FastAPI Server on http://localhost:8000 ...
        start "" "http://localhost:8000"
        python -m uvicorn main:app --host 0.0.0.0 --port 8000
        exit /b
    )
)

echo Opening NSE ALPHA-15 PRO Hybrid Terminal directly in Chrome...
start "" "%~dp0static\index.html"
