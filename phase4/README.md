# Phase 4: Multi-AMC & Fresh Data

Extends the crawl to **more AMCs** and **blog/help** (and optional comparison/calculator) pages. Chunks are stored in the **same Chroma collection** as Phase 1, so the Phase 2 chat sees all content. Scheduling is handled by Phase 3 (same scheduler; Phase 4 extends *what* is crawled).

## Scope (per architecture)

- **Multi-AMC:** Configurable list of fund URLs (Phase 1 URLs + Phase 4 extras). Add more AMCs by extending `EXTRA_FUND_URLS` in `phase4/config.py`.
- **Blog/help:** Exit load, expense ratio, taxation/capital gains articles from IndMoney blog.
- **Optional:** Comparison and calculator pages via `COMPARISON_CALCULATOR_URLS`.
- **Evaluation:** Held-out questions for accuracy and citation quality.

## Run pipeline (from project root)

```bash
# Crawl all Phase 4 URLs (funds + blog/help), parse, chunk, embed into same Chroma
python -m phase4.run_pipeline

# Load HTML from a directory instead of crawling (e.g. after saving to data/raw)
python -m phase4.run_pipeline --saved data/raw
```

Phase 4 uses **phase4_*** chunk ids so it **adds** to the existing collection without overwriting Phase 1 chunks. Run Phase 1 first so fund data exists; then run Phase 4 to add more funds and blog/help chunks.

## Config

Edit `phase4/config.py`:

- **FUND_URLS** – Phase 1 URLs + `EXTRA_FUND_URLS` (add more AMC fund URLs).
- **BLOG_HELP_URLS** – Blog/help article URLs.
- **COMPARISON_CALCULATOR_URLS** – Optional comparison/calculator pages.

Env (optional): `PHASE4_REQUEST_TIMEOUT`, `PHASE4_DELAY_SEC`, `PHASE4_CHUNK_SIZE`, `PHASE4_CHUNK_OVERLAP`.

## Evaluation

Run accuracy and citation checks on held-out questions:

```bash
# Default built-in questions
python -m phase4.evaluate

# Custom questions JSON: {"questions": [{"q": "...", "expected_keywords": ["..."]}]}
python -m phase4.evaluate --questions path/to/questions.json --output results.json
```

Metrics: **accuracy_keyword** (answer contains at least one expected keyword), **citation_rate** (answer has at least one source URL).

## Integration with Phase 3

To run Phase 4 after Phase 1 in the scheduler, set:

```bash
export PHASE3_RUN_PHASE4_AFTER=1
```

Then `python -m phase3.run_once` will run Phase 1 and, on success, run Phase 4 pipeline (so multi-AMC and blog/help are refreshed in the same job). Alternatively, add a separate cron job that runs `python -m phase4.run_pipeline` (e.g. weekly).

## Output

- **data/scraped_phase4.json** – Scraped fund docs + generic page count.
- **Chroma** – Same collection as Phase 1; new chunks have ids `phase4_0`, `phase4_1`, ...
