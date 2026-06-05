"""
Vercel Serverless Entry Point.

Vercel's @vercel/python builder detects `api/index.py` and exposes
the ASGI `app` object as a serverless function.

All /api/* and / routes are forwarded here via vercel.json.
Static files (/static/*) are served directly by Vercel's CDN.
"""

import sys
import os
from pathlib import Path

# Ensure the project root is on sys.path so `backend.*` imports resolve
# (Vercel runs from the project root, but guard against edge cases)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.main import app  # noqa: F401  — re-exported for Vercel
