@echo off
title BankEase - Simple Banking System
echo ===================================================
echo Starting BankEase Banking System...
echo ===================================================
echo.

python -m pip install flask werkzeug >nul 2>&1

echo Opening website in your default browser...
start http://127.0.0.1:5000/login

echo Starting Flask server...
python app.py
pause
