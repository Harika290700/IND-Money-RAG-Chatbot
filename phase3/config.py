"""Phase 3: Scheduler configuration from environment."""

import os
from pathlib import Path

# Project root (parent of phase3)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Pipeline mode: "full" = crawl then parse/chunk/embed; "from_json" = build from data/scraped_funds.json only
PIPELINE_MODE = os.environ.get("PHASE3_PIPELINE_MODE", "from_json").strip().lower()
if PIPELINE_MODE not in ("full", "from_json"):
    PIPELINE_MODE = "from_json"

# Max time (seconds) for one pipeline run; 0 = no limit
try:
    TIMEOUT_SEC = int(os.environ.get("PHASE3_TIMEOUT_SEC", "1800"))
except (TypeError, ValueError):
    TIMEOUT_SEC = 1800
if TIMEOUT_SEC < 0:
    TIMEOUT_SEC = 0

# Retries on failure (0 = no retries)
try:
    RETRIES = int(os.environ.get("PHASE3_RETRIES", "1"))
except (TypeError, ValueError):
    RETRIES = 1
if RETRIES < 0:
    RETRIES = 0

# Phase 2 backend base URL for refresh-complete callback (e.g. http://localhost:8000). Empty = skip.
PHASE2_BACKEND_URL = os.environ.get("PHASE2_BACKEND_URL", "").rstrip("/")

# Schedule: for in-process scheduler, run daily at this time (HH:MM, 24h). Default 10:00 (10 AM).
# For GitHub Actions, the schedule is set in .github/workflows/scheduler.yml (e.g. 10 AM UTC).
SCHEDULE_TIME = os.environ.get("PHASE3_SCHEDULE_TIME", "10:00").strip()

# Optional: cron expression for next-run calculation (e.g. "0 10 * * *" = daily 10 AM UTC).
SCHEDULE_CRON = os.environ.get("PHASE3_SCHEDULE_CRON", "").strip()
