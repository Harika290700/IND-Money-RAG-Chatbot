"""Phase 6: Audit log of Q&A for compliance and improvement."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from phase6.config import PHASE6_DIR, AUDIT_LOG_PATH


def log_qa(question: str, answer_snippet: str, session_id: Optional[str] = None) -> None:
    """
    Append one Q&A to the audit log (JSONL). Each line is a JSON object.
    answer_snippet: first N chars of the answer (e.g. 300) to avoid huge logs.
    """
    PHASE6_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "question": (question or "")[:500],
        "answer_snippet": (answer_snippet or "")[:300],
        "session_id": session_id or "",
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
