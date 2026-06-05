#!/bin/bash

# PromptForge Startup Helper for Linux / macOS

echo "==================================================="
echo "  PromptForge - Starting Local Development Server"
echo "==================================================="
echo

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    echo "[Info] .env file not found. Creating from .env.example..."
    cp .env.example .env
fi

# Detect virtual environment
if [ -d "venv" ]; then
    echo "[Info] Activating virtual environment (venv)..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "[Info] Activating virtual environment (.venv)..."
    source .venv/bin/activate
else
    echo "[Warning] Virtual environment not found."
    echo "[Info] Creating virtual environment (venv)..."
    python3 -m venv venv
    if [ -d "venv" ]; then
        echo "[Info] Activating newly created virtual environment..."
        source venv/bin/activate
    fi
fi

# Install dependencies
echo "[Info] Installing / updating dependencies..."
pip install -r requirements.txt

# Open default browser
echo "[Info] Opening browser to http://127.0.0.1:8000..."
if command -v xdg-open > /dev/null; then
    xdg-open http://127.0.0.1:8000 &
elif command -v open > /dev/null; then
    open http://127.0.0.1:8000 &
else
    echo "[Info] Please navigate to http://127.0.0.1:8000 in your browser."
fi

# Start uvicorn
echo "[Info] Starting Uvicorn backend server..."
python3 -m uvicorn backend.main:app --reload --port 8000
