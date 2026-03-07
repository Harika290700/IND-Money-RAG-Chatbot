"""Phase 4: Crawl extended URL list (funds + blog/help). Reuses fetch pattern from Phase 1."""

import time
from pathlib import Path
from typing import Optional

import httpx

from .config import (
    DELAY_BETWEEN_REQUESTS_SEC,
    RAW_HTML_DIR,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
)
from .urls import get_all_urls


def _url_to_slug(url: str) -> str:
    """Last path segment of URL, safe for filename."""
    return url.rstrip("/").split("/")[-1] or "page"


def fetch_page(url: str, client: Optional[httpx.Client] = None) -> tuple[str, int]:
    """Fetch a single page. Returns (html_content, status_code)."""
    kwargs = {
        "headers": REQUEST_HEADERS,
        "timeout": REQUEST_TIMEOUT,
        "follow_redirects": True,
    }
    if client is not None:
        r = client.get(url, **kwargs)
    else:
        with httpx.Client(**kwargs) as c:
            r = c.get(url)
    return r.text, r.status_code


def save_raw_html(url: str, html: str) -> Path | None:
    """Save raw HTML to data/raw/<slug>.html."""
    out_dir = Path(RAW_HTML_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _url_to_slug(url)
    path = out_dir / f"{slug}.html"
    path.write_text(html, encoding="utf-8", errors="replace")
    return path


def crawl_all(save_to_data_dir: bool = True, url_list: list[str] | None = None) -> list[tuple[str, str]]:
    """
    Crawl all Phase 4 URLs (funds + blog/help). Returns list of (url, html).
    If save_to_data_dir is True, writes each page to data/raw/<slug>.html.
    """
    urls = url_list if url_list is not None else get_all_urls()
    results = []
    with httpx.Client(
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:
        for url in urls:
            try:
                html, status = fetch_page(url, client=client)
                if status == 200 and html.strip():
                    results.append((url, html))
                    if save_to_data_dir:
                        p = save_raw_html(url, html)
                        if p:
                            print(f"  Saved: {p.name}")
                else:
                    print(f"  Skip {url}: status={status}")
            except Exception as e:
                print(f"  Error {url}: {e}")
            time.sleep(DELAY_BETWEEN_REQUESTS_SEC)
    return results
