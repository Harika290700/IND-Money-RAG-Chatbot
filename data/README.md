# Scraped data

This directory holds all scraped data from the IndMoney fund pages.

## Files

| File / folder | Description |
|---------------|-------------|
| **`scraped_funds.json`** | Parsed structured data for all funds. One JSON array of objects; each object has `url`, `fund_name`, `expense_ratio`, `benchmark`, `aum`, `min_lumpsum_sip`, `exit_load`, `lock_in`, `riskometer`, returns (lumpsum & SIP), `about_text`, `faq_text`, etc. Written by `run_pipeline.py` after parsing. |
| **`raw/`** | Raw HTML of each fund page, one file per URL. Filenames are the URL slug (e.g. `sbi-contra-fund-direct-growth-2612.html`). Written by the crawler when you run `run_pipeline.py` (live crawl). |

## When they are created

- **`scraped_funds.json`** – Created/overwritten every time the pipeline runs (crawl or `--saved`) after parsing. It contains one entry per fund URL (all 7 SBI funds). If a crawl times out for some URLs, run `python run_pipeline.py` again to refresh; the pipeline overwrites the file with whatever it successfully parses.
- **`raw/*.html`** – Created only when you run the pipeline **without** `--saved` (i.e. when crawling live). If you use `--saved samples`, HTML is read from the folder you pass; you can copy those into `data/raw/` if you want them here.

**SIP returns (1M, 3M, 6M, 1Y, 3Y, 5Y):** Filled for all funds where data was available. SBI Large & Midcap SIP returns are from IndMoney/user source; for other funds, SIP returns are either scraped from the page (when the performance section includes an SIP row) or estimated from lumpsum returns. Run the pipeline to refresh from live pages.

**Note:** All 7 SBI fund URLs are now in `scraped_funds.json` with full data. To refresh any fund, run `python run_pipeline.py` (live crawl).

## Loading the scraped data

```python
import json
from pathlib import Path

path = Path("data/scraped_funds.json")
funds = json.loads(path.read_text(encoding="utf-8"))
for f in funds:
    print(f["fund_name"], f["expense_ratio"], f["min_lumpsum_sip"])
```
