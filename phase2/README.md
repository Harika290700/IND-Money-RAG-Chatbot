# Phase 2: Chat Application – Backend & Frontend

Backend API and frontend chat UI for the RAG chatbot. Every response includes **source URL(s)** from the indexed IndMoney content. Answers are generated **only** from retrieved embeddings (via Groq when configured); personal information questions are out of scope.

## Prerequisites

- Phase 1 pipeline run at least once so `chroma_db/` and optionally `data/scraped_funds.json` exist at **project root**.
- **Groq (optional):** Set `GROQ_API_KEY` for LLM-generated answers. If unset, the backend falls back to returning the top retrieved chunk as the answer.

## Run from project root

```bash
# From project root ("Ind money RAG chatbot")
pip install -r requirements.txt

# Optional: set for Groq-generated answers (or put GROQ_API_KEY in project root .env)
export GROQ_API_KEY="your-groq-api-key"
export GROQ_MODEL="llama-3.1-8b-instant"   # default

# Start backend (serves API + frontend at /)
python -m uvicorn phase2.app:app --host 0.0.0.0 --port 8000
```

- **API:** `http://localhost:8000/chat` (POST), `http://localhost:8000/health` (GET)
- **Chat UI:** Open `http://localhost:8000/` in a browser.

## API (per architecture)

- **POST /chat**  
  - Body: `{ "message": "What is the expense ratio of SBI Contra Fund?", "session_id": "optional-for-multi-turn" }`  
  - Response: `{ "answer": "...", "sources": [{ "url": "...", "title": "...", "snippet": "..." }], "session_id": "..." }`  
  - Single-turn in MVP; optional `session_id` echoed for future multi-turn. Each source includes optional `snippet` (chunk excerpt) for citations.
- **GET /health**  
  Returns `{ "status": "ok" }` for load balancer/scheduler readiness.
- **POST /admin/refresh-complete**  
  Called by Phase 3 after data refresh (204 No Content).

Backend calls the RAG pipeline (retrieve from vector store, then LLM). The `/chat` handler runs the LLM in a thread pool so it is non-blocking. Timeouts and LLM failures return a graceful message in the response body (e.g. “Please try again.”) rather than a 5xx when possible.

## Config (env)

Variables can be set in the environment or in a **`.env`** file at the **project root** (same folder as `phase1/`, `phase2/`). The app loads `.env` on startup.

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key for LLM generation. If missing, answers use top chunk only. |
| `GROQ_MODEL` | Model name (default: `llama-3.1-8b-instant`). |
| `PHASE2_HOST` | Bind host (default: `0.0.0.0`). |
| `PHASE2_PORT` | Port (default: `8000`). |
| `PHASE2_LLM_TIMEOUT_SEC` | Timeout for LLM call in seconds (default: `30`). |
| `PHASE2_TOP_K` | Number of chunks to retrieve (default: `5`). |
| `PHASE2_SOURCE_SNIPPET_MAX_CHARS` | Max length of optional snippet per source (default: `200`; `0` to disable). |

## Behaviour

- **Answer only from embeddings:** The backend retrieves chunks from the Phase 1 vector store and (when Groq is configured) asks the LLM to answer only from that context. No general knowledge is used.
- **No personal information:** Queries that look like requests for personal/account/contact information get a single out-of-scope message; RAG/LLM is not called.
- **Error handling:** Timeouts, LLM failures, and empty retrieval produce graceful messages (“I couldn’t find…”, “Please try again.”) in the answer body; only unexpected server errors return 500.
- **Citations:** Every successful answer includes `sources` with `url`, `title`, and optional `snippet` for the IndMoney page(s) the information came from.

## Frontend

- Single-page chat UI at `/`: input, send, message list (user + assistant), **Sources** links under assistant messages, loading state, footer disclaimer.
- Served by the same FastAPI app; no separate build step. For a different backend origin, set `window.PHASE2_API_BASE` before the script runs (e.g. `https://api.example.com`).
