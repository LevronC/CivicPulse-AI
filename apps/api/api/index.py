"""
Vercel serverless entrypoint for the CivicPulse FastAPI app.

Vercel's Python runtime supports ASGI apps directly.
Set EMBEDDING_MODEL=heuristic on Vercel (ML deps excluded from bundle).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import app  # noqa: E402
