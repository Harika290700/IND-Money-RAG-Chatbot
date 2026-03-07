"""Phase 6: Feedback loop – thumbs up/down, report error."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from phase6.config import PHASE6_DIR, FEEDBACK_PATH


def record_feedback(
    question: str,
    rating: str,
    session_id: Optional[str] = None,
    comment: Optional[str] = None,
) -> None:
    """
    Record user feedback. rating: "up" | "down" | "report".
    Persists to feedback.jsonl (one JSON object per line).
    """
    if rating not in ("up", "down", "report"):
        rating = "down"
    PHASE6_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "question": (question or "")[:500],
        "rating": rating,
        "session_id": session_id or "",
        "comment": (comment or "")[:500] if comment else "",
    }
    with open(FEEDBACK_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
