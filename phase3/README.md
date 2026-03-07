# Phase 3: Data Refresh Scheduler

Runs the **Phase 1 pipeline** on a schedule so the vector store and RAG use up-to-date content from indmoney.com. On success, updates `data/structured/courses.json` (last_updated) and can notify the Phase 2 backend (`POST /admin/refresh-complete`).

## Option 1: GitHub Actions (10 AM daily) — recommended

The workflow **`.github/workflows/scheduler.yml`** runs at **10 AM UTC every day** (and on manual trigger).

- **Schedule:** `cron: "0 10 * * *"` (10 AM UTC). To use 10 AM IST instead, change to `"30 4 * * *"` (04:30 UTC).
- **Manual run:** Actions → Scheduler (10 AM daily) → Run workflow.
- **Requirements:** Commit `data/scraped_funds.json` for `from_json` mode, or set repo variable `PHASE3_PIPELINE_MODE=full` to run a full crawl in CI.
- **Overrides:** Set repository variables (Settings → Secrets and variables → Actions) e.g. `PHASE2_BACKEND_URL`, `PHASE3_RUN_PHASE4_AFTER`, `PHASE3_PIPELINE_MODE`.

No server or cron setup needed; GitHub runs the job and exits. **Note:** The job runs in a fresh runner each time, so `chroma_db` and `data/structured/courses.json` produced in the job are not persisted unless you add workflow steps to cache/restore them or to call an external refresh API on a server that has persistent storage.

## Option 2: One-shot (cron or Kubernetes CronJob)

Run the pipeline once and exit. Use with system cron or K8s CronJob.

```bash
# From project root
cd "Ind money RAG chatbot"
pip install -r requirements.txt

# Run once (mode from PHASE3_PIPELINE_MODE: full or from_json)
python -m phase3.run_once
```

- **Exit 0:** Pipeline finished successfully; last_updated written; refresh-complete called if `PHASE2_BACKEND_URL` is set.
- **Exit 1:** Pipeline failed or timed out (after retries).
- **Cwd:** `run_once` switches to project root so `data/` and `chroma_db/` resolve correctly (e.g. in CI).

## Option 3: In-process scheduler

One process runs forever and executes the pipeline daily at a fixed time (no cron needed).

```bash
# From project root
python -m phase3.scheduler
```

Pipeline runs every day at **PHASE3_SCHEDULE_TIME** (default **10:00**). Requires the `schedule` package (in requirements.txt).

## Configuration (env)

| Variable | Description | Default |
|----------|-------------|---------|
| `PHASE3_PIPELINE_MODE` | `full` = crawl then parse/chunk/embed; `from_json` = build from `data/scraped_funds.json` only | `from_json` |
| `PHASE3_TIMEOUT_SEC` | Max seconds for one pipeline run; 0 = no limit | `1800` (30 min) |
| `PHASE3_RETRIES` | Number of retries on failure | `1` |
| `PHASE2_BACKEND_URL` | Phase 2 base URL for `POST /admin/refresh-complete` (e.g. `http://localhost:8000`). Empty = skip. | (empty) |
| `PHASE3_SCHEDULE_TIME` | Daily run time for in-process scheduler (HH:MM, 24h) | `10:00` |
| `PHASE3_RUN_PHASE4_AFTER` | If set to `1` or `true`, run Phase 4 pipeline (multi-AMC + blog/help) after Phase 1 succeeds | (unset) |

## Example: system cron

Run every day at 10 AM (local time):

```bash
0 10 * * * cd /path/to/Ind\ money\ RAG\ chatbot && python -m phase3.run_once
```

Or use GitHub Actions (see Option 1) so the run happens at 10 AM UTC without a server.

## Behaviour

- **Idempotency:** Phase 1 pipeline does full replace/upsert; re-running produces a consistent state.
- **On success:** If `PHASE2_BACKEND_URL` is set, Phase 3 calls `POST /admin/refresh-complete` so the chat backend can invalidate caches (Phase 2 currently reads the vector store on each request, so this is optional).
- **On failure:** Errors are logged; exit code 1. The existing index is not replaced until a successful run.
- **Timeout:** If the pipeline runs longer than `PHASE3_TIMEOUT_SEC`, the run is considered failed and retries apply.

## See also

- `ARCHITECTURE.md` – Phase 3 architecture and downstream trigger behaviour.
