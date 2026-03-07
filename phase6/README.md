# Phase 6: Personalisation & Compliance

Implements **compliance**, **audit**, and **feedback** as per `ARCHITECTURE.md`.

## Implemented

- **Disclaimers:** Every chat answer includes a compliance disclaimer (no guarantee of returns; not investment advice). See `phase6/disclaimers.py` and integration in Phase 2 `_answer_with_disclaimer()`.
- **Audit log:** Each Q&A is logged to `data/phase6/audit_log.jsonl` (timestamp, question, answer snippet, session_id). See `phase6/audit.py`; Phase 2 calls `log_qa()` after each non-cached answer.
- **Feedback loop:** `POST /feedback` accepts `question`, `rating` (`up` | `down` | `report`), optional `session_id` and `comment`. Feedback is appended to `data/phase6/feedback.jsonl`. The chat UI shows “Was this helpful?” with thumbs up, thumbs down, and “Report error” on each assistant message.

## User context (planned)

- Logged-in user’s holdings (if permitted by product) are not implemented; no auth in this repo. Can be added when the product provides a user context API.

## Data paths

- `data/phase6/audit_log.jsonl` – one JSON object per line (ts, question, answer_snippet, session_id).
- `data/phase6/feedback.jsonl` – one JSON object per line (ts, question, rating, session_id, comment).

Create `data/phase6/` manually if needed; the code creates it on first write.
