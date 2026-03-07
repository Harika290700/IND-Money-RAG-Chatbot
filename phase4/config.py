"""
Phase 4: Multi-AMC & extended pages configuration.
Extends crawl to more AMCs and blog/help/comparison pages. Uses same Chroma collection as Phase 1.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Same data dir and Chroma as Phase 1 (Phase 4 adds/upserts into same collection)
DATA_DIR = PROJECT_ROOT / "data"
RAW_HTML_DIR = DATA_DIR / "raw"
SCRAPED_FUNDS_JSON = PROJECT_ROOT / "data" / "scraped_funds.json"
# Phase 4 extended scraped output (funds + generic pages metadata)
PHASE4_SCRAPED_JSON = PROJECT_ROOT / "data" / "scraped_phase4.json"

# Chroma: same collection so Phase 2 RAG sees all content
try:
    from phase1.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
except Exception:
    CHROMA_PERSIST_DIR = PROJECT_ROOT / "chroma_db"
    CHROMA_COLLECTION_NAME = "indmoney_funds"

# Chunk ids prefix so Phase 4 chunks don't overwrite Phase 1 (upsert adds new ids)
CHROMADB_ID_PREFIX = "phase4"

# --- Extended fund URLs (multi-AMC): add more AMCs here or load from Phase 1 + extra ---
# Include Phase 1 fund URLs so we can run Phase 4 as a full refresh, or only extras for incremental
try:
    from phase1.config import FUND_URLS as PHASE1_FUND_URLS
except Exception:
    PHASE1_FUND_URLS = []

# Additional fund URLs for more AMCs (IndMoney fund page URLs)
EXTRA_FUND_URLS = [
    # Example: add HDFC, Nippon, etc. when needed
    # "https://www.indmoney.com/mutual-funds/hdfc-index-fund-nifty-50-direct-plan-growth-2997",
]

# All fund URLs = Phase 1 + Phase 4 extra (no duplicates)
FUND_URLS = list(dict.fromkeys(PHASE1_FUND_URLS + EXTRA_FUND_URLS))

# --- Blog / help / supporting pages (from architecture) ---
BLOG_HELP_URLS = [
    "https://www.indmoney.com/blog/mutual-funds/exit-load-mutual-funds-explained",
    "https://www.indmoney.com/blog/mutual-funds/what-is-expense-ratio",
    "https://www.indmoney.com/blog/mutual-funds/taxation-on-mutual-funds-indmoney",
]

# Optional: comparison, calculator pages (add as needed)
COMPARISON_CALCULATOR_URLS = []

# Crawler (same as Phase 1)
REQUEST_TIMEOUT = int(os.environ.get("PHASE4_REQUEST_TIMEOUT", "30"))
DELAY_BETWEEN_REQUESTS_SEC = float(os.environ.get("PHASE4_DELAY_SEC", "1.0"))
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Chunking (align with Phase 1)
CHUNK_SIZE = int(os.environ.get("PHASE4_CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.environ.get("PHASE4_CHUNK_OVERLAP", "80"))
