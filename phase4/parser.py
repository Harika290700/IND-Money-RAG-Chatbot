"""Phase 4: Parse fund pages (Phase 1 parser) and generic blog/help pages."""

from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup


@dataclass
class GenericPage:
    """Parsed blog/help or comparison page."""
    url: str
    title: str
    text: str
    page_type: str  # "blog" | "help" | "comparison" | "calculator"


def parse_fund_page(url: str, html: str):
    """Delegate to Phase 1 fund page parser. Returns FundDocument or None."""
    from phase1.parser import parse_fund_page as phase1_parse
    return phase1_parse(url, html)


def _strip_text(s: str) -> str:
    return " ".join(s.split()) if s else ""


def parse_generic_page(url: str, html: str, page_type: str = "blog") -> Optional[GenericPage]:
    """
    Parse a non-fund page (blog, help, comparison) into title and main text.
    Returns GenericPage or None if no meaningful content.
    """
    soup = BeautifulSoup(html, "lxml")
    title = ""
    tit = soup.find("title")
    if tit and tit.string:
        title = _strip_text(tit.string)
    h1 = soup.find("h1")
    if h1 and h1.get_text():
        title = title or _strip_text(h1.get_text())

    # Main content: article, main, or body
    main = soup.find("article") or soup.find("main") or soup.find("body")
    if not main:
        return None
    text = main.get_text(separator="\n", strip=True)
    text = _strip_text(text)
    if len(text) < 100:
        return None
    return GenericPage(url=url, title=title or url, text=text, page_type=page_type)
