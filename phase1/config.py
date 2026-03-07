"""Phase 1 configuration: fund URLs and pipeline settings."""

from pathlib import Path

# Project root (parent of phase1)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Scraped data output (under project root)
DATA_DIR = PROJECT_ROOT / "data"
RAW_HTML_DIR = DATA_DIR / "raw"
SCRAPED_FUNDS_JSON = DATA_DIR / "scraped_funds.json"

# Mutual Fund pages to crawl (IndMoney) - SBI, ICICI, HDFC, Motilal Oswal, Canara Robeco
FUND_URLS = [
    # SBI
    "https://www.indmoney.com/mutual-funds/sbi-large-midcap-fund-direct-growth-2922",
    "https://www.indmoney.com/mutual-funds/sbi-nifty-midcap-150-index-fund-direct-growth-1041637",
    "https://www.indmoney.com/mutual-funds/sbi-contra-fund-direct-growth-2612",
    "https://www.indmoney.com/mutual-funds/sbi-large-cap-fund-direct-growth-3046",
    "https://www.indmoney.com/mutual-funds/sbi-small-cap-fund-direct-plan-growth-3603",
    "https://www.indmoney.com/mutual-funds/sbi-flexicap-fund-direct-growth-3249",
    "https://www.indmoney.com/mutual-funds/sbi-elss-tax-saver-fund-direct-growth-2754",
    # ICICI Prudential
    "https://www.indmoney.com/mutual-funds/icici-prudential-smallcap-fund-direct-plan-growth-3588",
    "https://www.indmoney.com/mutual-funds/icici-prudential-large-cap-fund-direct-plan-growth-2995",
    "https://www.indmoney.com/mutual-funds/icici-prudential-flexicap-fund-direct-growth-1006609",
    # HDFC
    "https://www.indmoney.com/mutual-funds/hdfc-flexi-cap-fund-direct-plan-growth-option-3184",
    "https://www.indmoney.com/mutual-funds/hdfc-mid-cap-fund-direct-plan-growth-option-3097",
    "https://www.indmoney.com/mutual-funds/hdfc-focused-fund-direct-plan-growth-option-2795",
    # Motilal Oswal
    "https://www.indmoney.com/mutual-funds/motilal-oswal-midcap-fund-direct-growth-1040897",
    "https://www.indmoney.com/mutual-funds/motilal-oswal-flexi-cap-fund-direct-growth-1040896",
    "https://www.indmoney.com/mutual-funds/motilal-oswal-nasdaq-100-fund-of-fund-direct-growth-1040009",
    # Canara Robeco
    "https://www.indmoney.com/mutual-funds/canara-robeco-large-cap-fund-direct-plan-growth-2949",
    "https://www.indmoney.com/mutual-funds/canara-robeco-mid-cap-fund-direct-growth-1042446",
    "https://www.indmoney.com/mutual-funds/canara-robeco-large-and-mid-cap-fund-direct-plan-growth-option-2852",
]

# Crawler
REQUEST_TIMEOUT = 30
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
DELAY_BETWEEN_REQUESTS_SEC = 1.0

# Chunking
CHUNK_SIZE = 512
CHUNK_OVERLAP = 80

# Vector store (under project root)
CHROMA_PERSIST_DIR = PROJECT_ROOT / "chroma_db"
CHROMA_COLLECTION_NAME = "indmoney_funds"

# RAG
TOP_K_RETRIEVAL = 5
