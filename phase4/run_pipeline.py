"""Phase 4: Multi-AMC & extended pages pipeline. Crawl, parse (fund + blog/help), chunk, embed into same Chroma."""

import json
import sys
from pathlib import Path

from .chunking import build_fund_chunks, build_generic_chunks
from .config import PHASE4_SCRAPED_JSON
from .crawl import crawl_all
from .embed_store import embed_and_store
from .parser import GenericPage, parse_fund_page, parse_generic_page
from .urls import get_all_urls, get_blog_help_urls, get_comparison_calculator_urls, get_fund_urls


def run(use_saved: str | None = None, from_json: bool = False):
    """
    Run Phase 4 pipeline: crawl extended URLs (funds + blog/help), parse, chunk, embed.
    Chunks are upserted with phase4_* ids into the same Chroma collection as Phase 1.
    - from_json: not used in Phase 4 (Phase 4 always crawls or uses saved HTML).
    - use_saved: load HTML from this directory instead of crawling.
    """
    print("Phase 4 pipeline: Multi-AMC + blog/help → Crawl → Parse → Chunk → Embed")
    fund_url_set = set(get_fund_urls())
    blog_help_set = set(get_blog_help_urls())
    comparison_set = set(get_comparison_calculator_urls())

    if use_saved:
        from phase1.run_pipeline import load_saved_html
        base = Path(use_saved)
        if not base.is_dir():
            print(f"Directory not found: {use_saved}")
            return
        pages = []
        for f in sorted(base.glob("*.html")):
            url = f"https://www.indmoney.com/mutual-funds/{f.stem}"
            html = f.read_text(encoding="utf-8", errors="replace")
            pages.append((url, html))
        print(f"Loaded {len(pages)} saved HTML files.")
    else:
        urls = get_all_urls()
        if not urls:
            print("No URLs configured. Add FUND_URLS and BLOG_HELP_URLS in phase4.config.")
            return
        print(f"Crawling {len(urls)} URLs...")
        pages = crawl_all(save_to_data_dir=True, url_list=urls)

    if not pages:
        print("No pages available.")
        return

    fund_documents = []
    generic_pages = []

    for url, html in pages:
        if url in fund_url_set:
            doc = parse_fund_page(url, html)
            if doc:
                fund_documents.append(doc)
                print(f"  Parsed fund: {doc.fund_name}")
            else:
                print(f"  Skip fund: {url}")
        else:
            page_type = "comparison" if url in comparison_set else "blog"
            gen = parse_generic_page(url, html, page_type=page_type)
            if gen:
                generic_pages.append(gen)
                print(f"  Parsed {page_type}: {gen.title[:50]}...")
            else:
                print(f"  Skip: {url}")

    # Save scraped fund data (same format as Phase 1 for fund docs)
    if fund_documents:
        scraped = [d.to_dict() for d in fund_documents]
        PHASE4_SCRAPED_JSON.parent.mkdir(parents=True, exist_ok=True)
        out_data = {"funds": scraped, "generic_count": len(generic_pages)}
        PHASE4_SCRAPED_JSON.write_text(json.dumps(out_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved {len(scraped)} funds + {len(generic_pages)} generic to {PHASE4_SCRAPED_JSON}")

    chunks = []
    chunks.extend(build_fund_chunks(fund_documents))
    chunks.extend(build_generic_chunks(generic_pages))

    if not chunks:
        print("No chunks produced. Exiting.")
        return

    print(f"Built {len(chunks)} chunks ({len(fund_documents)} fund docs, {len(generic_pages)} generic pages).")
    embed_and_store(chunks)
    try:
        from phase5.metadata import write_last_updated
        write_last_updated()
    except Exception:
        pass
    print("Done. Phase 4 chunks are in the same collection; Phase 2 RAG will see them.")


if __name__ == "__main__":
    use_saved = None
    args = sys.argv[1:]
    if "--saved" in args and len(args) > args.index("--saved") + 1:
        use_saved = args[args.index("--saved") + 1]
    run(use_saved=use_saved)
