"""
Application configuration — loads from environment variables.
Central source for all constants, model settings, and retry policies.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_APPS_DIR = BASE_DIR / "generated_apps"
EVAL_RESULTS_DIR = BASE_DIR / "backend" / "evaluation" / "results"

GENERATED_APPS_DIR.mkdir(exist_ok=True)
EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4o")
FAST_MODEL = os.getenv("FAST_MODEL", "gpt-4o-mini")
TEMPERATURE = 0
SEED = 42  # For deterministic outputs
MOCK_LLM = os.getenv("MOCK_LLM", "false").lower() in ("true", "1", "yes")

# --- Pipeline ---
MAX_RETRIES_PER_STAGE = 3
RETRY_BACKOFF_BASE = 1.5  # seconds — exponential backoff multiplier

# --- Cost tracking (per 1M tokens, USD) ---
MODEL_COSTS = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

# --- Server ---
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
