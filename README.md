# IndMoney RAG Chatbot

RAG chatbot for IndMoney mutual fund information. Code is organized by **phase** (see `ARCHITECTURE.md`). Every answer returns the **source URL(s)** the information came from.

## Project layout

- **`phase1/`** – Data pipeline & RAG: crawl, parse, chunk, embed, query. Chunks can be built from `data/scraped_funds.json`.
- **`phase2/`** – Chat application: FastAPI backend (`POST /chat`, `GET /health`) and chat UI; answers from RAG + Groq LLM, with source citations.
- **`phase3/`** – Data refresh scheduler: run Phase 1 pipeline on a schedule (cron or in-process); optional refresh-complete callback to Phase 2.
- **`phase4/`** – Multi-AMC & fresh data: extended fund URLs + blog/help pages, same Chroma collection; evaluation script.
- **`phase5/`** – UX & scale: last_updated (data/structured/courses.json), GET /meta, cache, rate limit.
- **`phase6/`** – Personalisation & compliance: disclaimers, audit log, feedback (thumbs up/down, report error).
- **`data/`** – `scraped_funds.json` and `data/raw/` (raw HTML). Shared by Phase 1.
- **`ARCHITECTURE.md`** – Phase-wise architecture.

## Phases implemented (summary)

| Phase | Name | Status | What’s implemented |
|-------|------|--------|--------------------|
| **1** | Data & core RAG | ✅ Done | Crawl/parse IndMoney fund pages → `scraped_funds.json`; chunk, embed (Chroma); query script; RAG retrieval with source URLs. |
| **2** | Chat app (backend + frontend) | ✅ Done | FastAPI `POST /chat`, `GET /health`, `GET /meta`; chat UI at `/`; RAG + Groq LLM; fallback from `scraped_funds.json`; one relevant source link; answers only for mutual-fund questions. |
| **3** | Data refresh scheduler | ✅ Done | `run_once` (one-shot pipeline); in-process scheduler; optional `POST /admin/refresh-complete`; GitHub Actions workflow. |
| **4** | Multi-AMC & extended data | ✅ Done | Extended crawl (more AMCs, blog/help); same Chroma collection; `evaluate` script for held-out questions. |
| **5** | UX & scale | ✅ Done | `data/structured/courses.json` last_updated; GET `/meta`; response cache for `/chat`; rate limit (60/min per IP); cache clear on refresh-complete. |
| **6** | Personalisation & compliance | ✅ Done | Compliance disclaimer on every answer; audit log (Q&A to `data/phase6/audit_log.jsonl`); `POST /feedback` (up/down/report); thumbs up/down and “Report error” in UI. |

## Setup

```bash
cd "Ind money RAG chatbot"
python3 -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Phase 1: Run pipeline and query

From **project root**:

```bash
# Crawl URLs, parse, save to data/scraped_funds.json, then chunk and embed
python -m phase1.run_pipeline

# Or: build chunks only from existing data/scraped_funds.json (no crawl)
# Use this after updating scraped_funds.json so the vector store matches the JSON.
python -m phase1.run_pipeline --from-json

# Query – every answer includes Source URL(s)
python -m phase1.query "What is the expense ratio of SBI Contra Fund?"
python -m phase1.query "What is the minimum SIP for ICICI Large Cap Fund?"
```

## Are chunks based on updated scraped_funds.json?

- **Yes, if you run** `python -m phase1.run_pipeline --from-json` **after updating** `data/scraped_funds.json`. That command builds chunks only from that file and re-embeds into Chroma, so the RAG index and every answer’s source URL reflect the updated data.
- If you only run `run_pipeline.py` (without `--from-json`), chunks are built from the crawl/parse run and the same data is written to `scraped_funds.json`, so they stay in sync.
- If you edit `scraped_funds.json` by hand and never run `--from-json`, the vector store is **not** updated; run `run_pipeline.py --from-json` to refresh it.

## Source URLs

Every query response lists **Source URL(s)** – the IndMoney page(s) the answer was retrieved from. Chunk metadata stores `source_url`; the RAG layer returns it for each source.

## Data

- **`data/scraped_funds.json`** – Structured data for all funds (SBI + ICICI Prudential). See `data/README.md`.
- **`data/raw/`** – Raw HTML per fund page (when using live crawl).

## Phase 2: Chat app (backend + frontend)

One server serves **both** the API and the chat UI. From **project root** (after Phase 1 pipeline has been run at least once):

```bash
# Activate venv if you use one
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

# Install dependencies if needed
pip install -r requirements.txt

# Optional: set for LLM-generated answers (or add GROQ_API_KEY to project root .env)
export GROQ_API_KEY="your-groq-api-key"

# Start backend and frontend (API at :8000, chat UI at /)
python -m uvicorn phase2.app:app --host 0.0.0.0 --port 8000
```

Or run the script: `./run_app.sh`

- **Chat UI:** http://localhost:8000/
- **API:** http://localhost:8000/chat (POST), http://localhost:8000/health (GET)

**Stop the application:** Press **Ctrl+C** in the terminal where the server is running.

See `phase2/README.md` for API and config.

## Phase 3: Data refresh scheduler

Run the Phase 1 pipeline on a schedule so the vector store stays up to date.

**One-shot (for cron or Kubernetes CronJob):**
```bash
python -m phase3.run_once
```

**In-process (daily at 02:00 by default):**
```bash
python -m phase3.scheduler
```

Set `PHASE3_PIPELINE_MODE` to `full` or `from_json`, and optionally `PHASE2_BACKEND_URL` so Phase 3 calls `POST /admin/refresh-complete` after a successful run. See `phase3/README.md`.

## Testing

From project root:

```bash
pip install -r requirements.txt
pytest tests/ -v
```

To skip integration tests (which require the vector store to be built):

```bash
pytest tests/ -v -m "not integration"
```

Example test case **"What is the nav for icici large cap fund?"** is covered in Phase 1, Phase 2, and integration tests. See `tests/README.md`.

## Phase 4: Multi-AMC & extended pages

Extend the crawl to more AMCs and blog/help pages. Chunks go into the **same** Chroma collection, so the chat sees everything.

```bash
# Crawl Phase 4 URLs (funds + blog/help), parse, chunk, embed
python -m phase4.run_pipeline

# Evaluation on held-out questions
python -m phase4.evaluate
python -m phase4.evaluate --questions phase4/questions_example.json --output eval_results.json
```

Optional: set `PHASE3_RUN_PHASE4_AFTER=1` so Phase 3 runs Phase 4 after Phase 1. See `phase4/README.md`.

## Phase 5: Last updated & scale

- **Data last updated:** The scheduler (and Phase 1/4 pipelines) write **data/structured/courses.json** with `last_updated`. The frontend shows "Data last updated: …" from **GET /meta**.
- **Scale:** Response cache for `/chat`; rate limit 60/min per IP; cache cleared when Phase 3 runs refresh-complete.
- See `phase5/README.md`.

## Troubleshooting

### Chroma: "Your system has an unsupported version of sqlite3. Chroma requires sqlite3 >= 3.35.0"

Chroma needs SQLite ≥ 3.35. macOS (and some Linux) often ship with an older SQLite. Two options:

**Option A – Use a newer SQLite via pysqlite3 (when available)**  
The app is set up to use `pysqlite3` if installed. Install it only if your platform has a wheel (e.g. many Linux images, or Python 3.9+ on some Macs):

```bash
pip install pysqlite3-binary
```

Then run the app as usual. If `pip install pysqlite3-binary` fails with "No matching distribution", use Option B.

**Option B – Upgrade SQLite and use a Python linked to it (macOS)**  
1. Install a newer SQLite: `brew install sqlite`  
2. Use a Python built against that SQLite. E.g. with **pyenv**:  
   `brew install pyenv` then `pyenv install 3.11` (pyenv’s Python will use Homebrew’s sqlite if available), create a venv with that Python, and run the app from that venv.  
3. Or install **Python from python.org** (installer often uses a newer SQLite) and create a venv with that interpreter.

See also: [Chroma troubleshooting – SQLite](https://docs.trychroma.com/troubleshooting#sqlite).

## Deploy on Vercel

The chatbot can be deployed to [Vercel](https://vercel.com) as a serverless app (single FastAPI function).

**1. Prerequisites**
- Ensure `data/scraped_funds.json` is committed (required for answers; Chroma is optional—the app falls back to JSON if the vector store is missing).
- Optional: run `python -m phase1.run_pipeline --from-json` locally and commit `chroma_db/` for vector search (larger deploy).

**2. Deploy**
- Push the repo to GitHub and [import the project on Vercel](https://vercel.com/new), or use the CLI:
  ```bash
  npm i -g vercel
  vercel
  ```
- Add **environment variables** in the Vercel project:
  - `GROQ_API_KEY` – your [Groq](https://console.groq.com) API key (for LLM answers).

**3. Entrypoint**
- `index.py` at the project root exposes the Phase 2 FastAPI app; Vercel detects it and deploys the app as one serverless function. The same app serves the chat UI at `/` and the API at `/chat`, `/health`, `/meta`, `/feedback`.

**4. Limits**
- Vercel Functions have size and timeout limits. If the bundle is too large (e.g. with Chroma + sentence-transformers), rely on the JSON fallback and omit `chroma_db/` from the repo (see `.vercelignore`). Audit and feedback logs under `data/phase6/` are written at runtime where the filesystem is writable.

## Deploy on Streamlit

The chatbot can run as a [Streamlit](https://streamlit.io) app (same RAG and chat logic, no FastAPI).

**1. Local run**
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
- Open the URL shown (e.g. http://localhost:8501). Set `GROQ_API_KEY` in `.env` or in the environment for LLM answers.

**2. Deploy on Streamlit Community Cloud**
- Push the repo to GitHub.
- Go to [share.streamlit.io](https://share.streamlit.io), sign in, and **New app**.
- Set **Repository** to your repo, **Branch** to `main`, **Main file path** to `streamlit_app.py`.
- Add **Secrets** (or in the app’s Advanced settings): `GROQ_API_KEY` = your Groq API key.
- Deploy. Ensure `data/scraped_funds.json` is in the repo (and optionally `chroma_db/` for vector search).

**3. Behaviour**
- `streamlit_app.py` uses the same `phase2.rag_service.chat()` and Phase 6 feedback. Sidebar has suggested questions and “New chat”; the main area has the four topic buttons (ask for fund then answer) and the chat. Source link is shown under each answer; thumbs up/down record feedback.

## Next

- Further phases per `ARCHITECTURE.md`.
