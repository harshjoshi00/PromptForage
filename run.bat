@echo off
title PromptForge Startup Helper
echo ===================================================
echo   PromptForge - Starting Local Development Server
echo ===================================================
echo.

:: Check if .env exists, if not create it from .env.example
if not exist .env (
    echo [Info] .env file not found. Creating from .env.example...
    copy .env.example .env
)

:: Check for virtual environment
if exist venv (
    echo [Info] Activating virtual environment...
    call venv\Scripts\activate
) else if exist .venv (
    echo [Info] Activating virtual environment...
    call .venv\Scripts\activate
) else (
    echo [Warning] Virtual environment not found. Running with global python.
    echo [Info] Creating virtual environment (venv)...
    python -m venv venv
    if exist venv (
        echo [Info] Activating newly created virtual environment...
        call venv\Scripts\activate
    )
)

:: Install/Upgrade dependencies
echo [Info] Installing / updating dependencies...
pip install -r requirements.txt

:: Open default browser in 3 seconds in the background
echo [Info] Opening browser to http://127.0.0.1:8000...
start "" http://127.0.0.1:8000

:: Start Uvicorn server
echo [Info] Starting Uvicorn backend server...
python -m uvicorn backend.main:app --reload --port 8000

pause
