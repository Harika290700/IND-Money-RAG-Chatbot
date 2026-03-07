"""
Phase 3: In-process scheduler that runs the Phase 1 pipeline at a fixed time each day.
Alternative to system cron: run this process and it will execute the pipeline at PHASE3_SCHEDULE_TIME (e.g. 02:00).
"""

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from phase3.config import SCHEDULE_TIME
from phase3.run_once import main as run_once_main


def _parse_schedule_time(s: str) -> tuple[int, int]:
    """Parse HH:MM (24h) into (hour, minute). Default (10, 0) for 10 AM."""
    s = (s or "10:00").strip()
    try:
        part = s.split(":")
        h = int(part[0]) % 24
        m = int(part[1]) % 60 if len(part) > 1 else 0
        return (h, m)
    except (ValueError, IndexError):
        return (10, 0)


def run_scheduler() -> None:
    """Run pipeline at SCHEDULE_TIME every day; block forever."""
    hour, minute = _parse_schedule_time(SCHEDULE_TIME)
    print(f"[phase3] Scheduler started. Pipeline will run daily at {hour:02d}:{minute:02d}.")

    try:
        import schedule
    except ImportError:
        print("[phase3] Install 'schedule' for in-process scheduling: pip install schedule", file=sys.stderr)
        print("[phase3] Or use cron to run: python -m phase3.run_once", file=sys.stderr)
        sys.exit(1)

    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(run_once_main)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    run_scheduler()
