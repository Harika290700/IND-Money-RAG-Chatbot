"""
Phase 5: Index metadata (last_updated) in data/structured/courses.json.
Written by Phase 3 scheduler and by Phase 1/4 pipelines on successful run so the frontend can show "Data last updated: …".
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STRUCTURED_DIR = ROOT / "data" / "structured"
COURSES_JSON = STRUCTURED_DIR / "courses.json"


def get_metadata_path() -> Path:
    return COURSES_JSON


def read_metadata() -> dict:
    """Read data/structured/courses.json. Returns dict with last_updated (or empty)."""
    p = get_metadata_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_last_updated() -> str | None:
    """Return last_updated value (ISO string) or None."""
    return read_metadata().get("last_updated")


def write_last_updated(ts: datetime | None = None) -> None:
    """Write last_updated to data/structured/courses.json. Called by scheduler and pipelines after successful refresh."""
    STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)
    if ts is None:
        ts = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    iso = ts.isoformat().replace("+00:00", "Z")
    data = read_metadata()
    data["last_updated"] = iso
    get_metadata_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
