"""Phase 1: Run pipeline — crawl/parse or load from scraped_funds.json, then chunk and embed."""
# Use pysqlite3 so Chroma gets SQLite >= 3.35 on systems with older bundled sqlite3
try:
    import pysqlite3
    import sys
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import json
import sys
from pathlib import Path

from .chunking import build_all_chunks, build_chunks_from_scraped_json


def _update_last_updated():
    """Update data/structured/courses.json last_updated so frontend can display it."""
    try:
        from phase5.metadata import write_last_updated
        write_last_updated()
    except Exception:
        pass
from .config import SCRAPED_FUNDS_JSON
from .crawler import crawl_all_fund_pages
from .embed_store import embed_and_store
from .parser import parse_fund_page


def load_saved_html(dir_path: str) -> list[tuple[str, str]]:
    """Load (url, html) from saved HTML files."""
    from .config import FUND_URLS

    base = Path(dir_path)
    if not base.is_dir():
        return []
    pages = []
    for f in sorted(base.glob("*.html")):
        url = None
        for u in FUND_URLS:
            if f.stem in u or u.split("/")[-1].replace("-", "_") in f.stem.replace("-", "_"):
                url = u
                break
        if not url:
            url = f"https://www.indmoney.com/mutual-funds/{f.stem}"
        html = f.read_text(encoding="utf-8", errors="replace")
        pages.append((url, html))
    return pages


def run(use_saved: str | None = None, from_json: bool = False):
    """
    Run Phase 1 pipeline.
    - from_json: build chunks from data/scraped_funds.json only (no crawl). Use this so
      the vector store is based on the updated scraped data; every answer will then
      return the correct source URL from that data.
    - use_saved: load HTML from this directory instead of crawling.
    """
    print("Phase 1 pipeline: Chunk → Embed → Store")
    if from_json:
        print("Building chunks from data/scraped_funds.json (vector store will match updated scraped data).")
        chunks = build_chunks_from_scraped_json()
        if not chunks:
            print("No data in scraped_funds.json or file missing. Run without --from-json first or add data.")
            return
        print(f"Built {len(chunks)} chunks from scraped_funds.json.")
        embed_and_store(chunks)
        _update_last_updated()
        print("Done. Chunks are now based on scraped_funds.json. Run query.py to ask questions.")
        return

    if use_saved:
        print(f"Loading saved HTML from: {use_saved}")
        pages = load_saved_html(use_saved)
        if not pages:
            print("No HTML files found.")
            return
    else:
        print("Crawling...")
        pages = crawl_all_fund_pages()
    if not pages:
        print("No pages available.")
        return
    print(f"Loaded {len(pages)} pages.")

    print("Parsing...")
    documents = []
    for url, html in pages:
        doc = parse_fund_page(url, html)
        if doc:
            documents.append(doc)
            print(f"  Parsed: {doc.fund_name} ({doc.expense_ratio or 'N/A'} exp ratio)")
        else:
            print(f"  Skip: {url}")

    if not documents:
        print("No documents parsed. Exiting.")
        return

    SCRAPED_FUNDS_JSON.parent.mkdir(parents=True, exist_ok=True)
    scraped = [doc.to_dict() for doc in documents]
    SCRAPED_FUNDS_JSON.write_text(json.dumps(scraped, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved scraped data to {SCRAPED_FUNDS_JSON} ({len(scraped)} funds).")

    print("Chunking...")
    chunks = build_all_chunks(documents)
    print(f"Built {len(chunks)} chunks.")

    print("Embedding and storing...")
    embed_and_store(chunks)
    _update_last_updated()
    print("Done. Run: python query.py \"What is the expense ratio of SBI Contra Fund?\"")


if __name__ == "__main__":
    use_saved = None
    from_json = False
    args = sys.argv[1:]
    if "--from-json" in args:
        from_json = True
        args = [a for a in args if a != "--from-json"]
    if "--saved" in args and len(args) > args.index("--saved") + 1:
        use_saved = args[args.index("--saved") + 1]
    run(use_saved=use_saved, from_json=from_json)
