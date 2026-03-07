"""
Phase 3: Run Phase 1 pipeline once with timeout and retries.
On success, optionally call Phase 2 POST /admin/refresh-complete and optionally run Phase 4.
Exit 0 on success, non-zero on failure (for cron/Kubernetes).
"""

import os
import sys
import threading
from pathlib import Path

# Ensure project root on path and (for CI) set cwd so data/ and chroma_db/ resolve
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
# Run from project root so Phase 1/4 find data/ and chroma_db/ when using relative paths
try:
    os.chdir(_ROOT)
except Exception:
    pass

from phase3.config import (
    PHASE2_BACKEND_URL,
    PIPELINE_MODE,
    RETRIES,
    TIMEOUT_SEC,
)


def _run_pipeline() -> None:
    """Invoke Phase 1 pipeline (mode from config)."""
    from phase1.run_pipeline import run
    run(from_json=(PIPELINE_MODE == "from_json"))


def _notify_refresh_complete() -> bool:
    """POST to Phase 2 /admin/refresh-complete. Returns True if called and 2xx."""
    if not PHASE2_BACKEND_URL:
        return True
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{PHASE2_BACKEND_URL}/admin/refresh-complete",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        print(f"[phase3] WARNING: refresh-complete failed: {e}", file=sys.stderr)
        return False


def run_with_timeout() -> bool:
    """
    Run pipeline in a thread; return True if it finished within TIMEOUT_SEC.
    On timeout, we cannot easily kill the thread (Python), so we return False
    and the process may still be doing work until it exits.
    """
    result = {"done": False, "error": None}

    def target():
        try:
            _run_pipeline()
            result["done"] = True
        except Exception as e:
            result["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=TIMEOUT_SEC if TIMEOUT_SEC else None)
    if not thread.is_alive():
        return result["done"]
    print("[phase3] Pipeline run timed out.", file=sys.stderr)
    if result.get("error"):
        print(f"[phase3] Error before timeout: {result['error']}", file=sys.stderr)
    return False


def main() -> int:
    last_error = None
    for attempt in range(RETRIES + 1):
        if attempt > 0:
            print(f"[phase3] Retry {attempt}/{RETRIES}...")
        try:
            if run_with_timeout():
                _notify_refresh_complete()
                if os.environ.get("PHASE3_RUN_PHASE4_AFTER", "").strip().lower() in ("1", "true", "yes"):
                    try:
                        from phase4.run_pipeline import run as phase4_run
                        print("[phase3] Running Phase 4 (multi-AMC + blog/help)...")
                        phase4_run()
                    except Exception as e:
                        print(f"[phase3] Phase 4 run failed (non-fatal): {e}", file=sys.stderr)
                try:
                    from phase5.metadata import write_last_updated
                    write_last_updated()
                    print("[phase3] Updated data/structured/courses.json (last_updated).")
                except Exception as e:
                    print(f"[phase3] WARNING: could not update last_updated: {e}", file=sys.stderr)
                print("[phase3] Pipeline finished successfully.")
                return 0
        except Exception as e:
            last_error = e
            print(f"[phase3] Run failed: {e}", file=sys.stderr)
    if last_error:
        print(f"[phase3] Final error: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
