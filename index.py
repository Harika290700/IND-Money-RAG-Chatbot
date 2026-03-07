"""
Vercel serverless entrypoint: expose the Phase 2 FastAPI app.
Vercel detects this file and runs the app as a single serverless function.
"""
from pathlib import Path
import sys

# Ensure project root is on path when Vercel runs this file
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from phase2.app import app

__all__ = ["app"]
