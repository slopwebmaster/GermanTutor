@echo off
title German Course Helper
cd /d "%~dp0"

:: Check if virtual environment exists, if not create it
if not exist "venv\Scripts\activate.bat" (
    echo First time setup: Installing Python dependencies...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: Run the app
python run.py
pause