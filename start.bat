@echo off
title NSE 15-AI-Agent & SMC Trading Terminal
echo ========================================================
echo       NSE 15-AI-AGENT & 5 SMC STRATEGY TRADING TERMINAL
echo ========================================================
echo.
cd /d "%~dp0"
echo Starting FastAPI Web Server & Multi-Agent Engine...
echo.
echo PC Access:     http://127.0.0.1:8000
echo Mobile Access: http://10.43.84.128:8000
echo (Connect your phone to the same Wi-Fi/Hotspot)
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
