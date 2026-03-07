"""Phase 6 configuration: paths for audit log and feedback store."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PHASE6_DIR = DATA_DIR / "phase6"
AUDIT_LOG_PATH = PHASE6_DIR / "audit_log.jsonl"
FEEDBACK_PATH = PHASE6_DIR / "feedback.jsonl"
