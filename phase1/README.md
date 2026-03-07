# Phase 1: Data & RAG Pipeline

Crawl IndMoney fund pages, parse to structured data, chunk, embed, and store in Chroma. Query returns answers with **source URL(s)** for every response.

## Chunks based on `scraped_funds.json`

The vector store (Chroma) can be built in two ways:

1. **Crawl then build** – `python run_pipeline.py` crawls URLs, parses HTML, saves to `data/scraped_funds.json`, then builds chunks and embeds. Chunks match the saved JSON.

2. **Build from JSON only** – `python run_pipeline.py --from-json` builds chunks **only** from `data/scraped_funds.json` and re-embeds. Use this after you update `data/scraped_funds.json` so that **chunks (and source URLs in answers) are based on the updated scraped data**.

## Run from project root

```bash
# From project root
cd "Ind money RAG chatbot"
pip install -r requirements.txt

# Option A: Crawl, parse, save JSON, then chunk and embed
python -m phase1.run_pipeline

# Option B: Build chunks from existing data/scraped_funds.json and embed (no crawl)
python -m phase1.run_pipeline --from-json

# Query (always returns source URL(s) for the answer)
python -m phase1.query "What is the expense ratio of SBI Contra Fund?"
```

Paths in `config.py` point to project root `data/` and `chroma_db/`. Use the **project root** commands above so that the `phase1` package and its imports resolve correctly.

## Source URLs

Every answer from `query.py` (or from `rag.ask()`) includes a **Source URL(s)** section listing the IndMoney page(s) the information came from. Chunk metadata stores `source_url`; the RAG response returns it for each source.
