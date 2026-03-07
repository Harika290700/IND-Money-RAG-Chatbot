"""Phase 1: Parse IndMoney fund page HTML into structured data and clean text."""

import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup


@dataclass
class FundDocument:
    """Structured fund data plus text for RAG."""

    url: str
    fund_name: str
    category: str
    amc: str
    nav: str
    nav_date: str
    since_inception_return: str
    expense_ratio: str
    benchmark: str
    aum: str
    inception_date: str
    min_lumpsum_sip: str
    exit_load: str
    lock_in: str
    turnover: str
    riskometer: str
    investor_snippet: str  # e.g. "11672 people have invested ₹ 12.1Cr in ..."
    # Returns: lumpsum 1M, 3M, 6M, 1Y, 3Y, 5Y
    returns_lumpsum_1m: str = ""
    returns_lumpsum_3m: str = ""
    returns_lumpsum_6m: str = ""
    returns_lumpsum_1y: str = ""
    returns_lumpsum_3y: str = ""
    returns_lumpsum_5y: str = ""
    returns_sip_1m: str = ""
    returns_sip_3m: str = ""
    returns_sip_6m: str = ""
    returns_sip_1y: str = ""
    returns_sip_3y: str = ""
    returns_sip_5y: str = ""
    about_text: str = ""
    faq_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Full dict for JSON serialization (scraped data file)."""
        return {
            "url": self.url,
            "fund_name": self.fund_name,
            "category": self.category,
            "amc": self.amc,
            "nav": self.nav,
            "nav_date": self.nav_date,
            "since_inception_return": self.since_inception_return,
            "expense_ratio": self.expense_ratio,
            "benchmark": self.benchmark,
            "aum": self.aum,
            "inception_date": self.inception_date,
            "min_lumpsum_sip": self.min_lumpsum_sip,
            "exit_load": self.exit_load,
            "lock_in": self.lock_in,
            "turnover": self.turnover,
            "riskometer": self.riskometer,
            "investor_snippet": self.investor_snippet,
            "returns_lumpsum_1m": self.returns_lumpsum_1m,
            "returns_lumpsum_3m": self.returns_lumpsum_3m,
            "returns_lumpsum_6m": self.returns_lumpsum_6m,
            "returns_lumpsum_1y": self.returns_lumpsum_1y,
            "returns_lumpsum_3y": self.returns_lumpsum_3y,
            "returns_lumpsum_5y": self.returns_lumpsum_5y,
            "returns_sip_1m": self.returns_sip_1m,
            "returns_sip_3m": self.returns_sip_3m,
            "returns_sip_6m": self.returns_sip_6m,
            "returns_sip_1y": self.returns_sip_1y,
            "returns_sip_3y": self.returns_sip_3y,
            "returns_sip_5y": self.returns_sip_5y,
            "about_text": self.about_text,
            "faq_text": self.faq_text,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FundDocument":
        """Build FundDocument from a dict (e.g. loaded from scraped_funds.json)."""
        return cls(
            url=d.get("url", ""),
            fund_name=d.get("fund_name", ""),
            category=d.get("category", ""),
            amc=d.get("amc", ""),
            nav=d.get("nav", ""),
            nav_date=d.get("nav_date", ""),
            since_inception_return=d.get("since_inception_return", ""),
            expense_ratio=d.get("expense_ratio", ""),
            benchmark=d.get("benchmark", ""),
            aum=d.get("aum", ""),
            inception_date=d.get("inception_date", ""),
            min_lumpsum_sip=d.get("min_lumpsum_sip", ""),
            exit_load=d.get("exit_load", ""),
            lock_in=d.get("lock_in", ""),
            turnover=d.get("turnover", ""),
            riskometer=d.get("riskometer", ""),
            investor_snippet=d.get("investor_snippet", ""),
            returns_lumpsum_1m=d.get("returns_lumpsum_1m", ""),
            returns_lumpsum_3m=d.get("returns_lumpsum_3m", ""),
            returns_lumpsum_6m=d.get("returns_lumpsum_6m", ""),
            returns_lumpsum_1y=d.get("returns_lumpsum_1y", ""),
            returns_lumpsum_3y=d.get("returns_lumpsum_3y", ""),
            returns_lumpsum_5y=d.get("returns_lumpsum_5y", ""),
            returns_sip_1m=d.get("returns_sip_1m", ""),
            returns_sip_3m=d.get("returns_sip_3m", ""),
            returns_sip_6m=d.get("returns_sip_6m", ""),
            returns_sip_1y=d.get("returns_sip_1y", ""),
            returns_sip_3y=d.get("returns_sip_3y", ""),
            returns_sip_5y=d.get("returns_sip_5y", ""),
            about_text=d.get("about_text", ""),
            faq_text=d.get("faq_text", ""),
        )

    def to_metadata(self) -> dict[str, Any]:
        """Metadata for vector store (flat, serializable). Used for RAG and returning scraped data + link."""
        return {
            "source_url": self.url,
            "fund_name": self.fund_name,
            "amc": self.amc,
            "category": self.category,
            "expense_ratio": self.expense_ratio,
            "benchmark": self.benchmark,
            "riskometer": self.riskometer,
            "lock_in": self.lock_in,
            "min_sip": self.min_lumpsum_sip,
            "nav": self.nav,
            "nav_date": self.nav_date,
            "exit_load": self.exit_load,
            "aum": self.aum,
        }

    def to_document_text(self) -> str:
        """Single coherent text for chunking and retrieval."""
        lines = [
            f"Fund: {self.fund_name}",
            f"Category: {self.category}",
            f"AMC: {self.amc}",
            f"NAV: {self.nav} (as on {self.nav_date}). Since inception return: {self.since_inception_return}.",
            self.investor_snippet,
            "",
            "Key metrics:",
            f"Expense ratio: {self.expense_ratio}",
            f"Benchmark: {self.benchmark}",
            f"AUM: {self.aum}",
            f"Inception Date: {self.inception_date}",
            f"Min Lumpsum/SIP: {self.min_lumpsum_sip}",
            f"Exit Load: {self.exit_load}",
            f"Lock In: {self.lock_in}",
            f"TurnOver: {self.turnover}",
            f"Risk (Riskometer): {self.riskometer}",
            "",
            "Lumpsum returns:",
            f"1M: {self.returns_lumpsum_1m}, 3M: {self.returns_lumpsum_3m}, 6M: {self.returns_lumpsum_6m}, "
            f"1Y: {self.returns_lumpsum_1y}, 3Y: {self.returns_lumpsum_3y}, 5Y: {self.returns_lumpsum_5y}",
            "",
            "SIP returns:",
            f"1M: {self.returns_sip_1m}, 3M: {self.returns_sip_3m}, 6M: {self.returns_sip_6m}, "
            f"1Y: {self.returns_sip_1y}, 3Y: {self.returns_sip_3y}, 5Y: {self.returns_sip_5y}",
        ]
        if self.about_text:
            lines.extend(["", "About:", self.about_text])
        if self.faq_text:
            lines.extend(["", "FAQs:", self.faq_text])
        return "\n".join(lines).strip()


def _text(soup: BeautifulSoup) -> str:
    return soup.get_text(separator=" ", strip=True) if soup else ""


def _re_first(text: str, pattern: str, group: int = 1) -> str:
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    if group == 0 or m.lastindex is None or group > m.lastindex:
        return m.group(0).strip()
    return m.group(group).strip()


def _re_first_multiple(text: str, patterns: list[tuple[str, int]]) -> str:
    for pattern, group in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            if group == 0 or m.lastindex is None or group > m.lastindex:
                s = m.group(0).strip()
            else:
                s = m.group(group).strip()
            if s:
                return s
    return ""


def _fund_name_from_url(url: str) -> str:
    """Derive a readable fund name from the URL slug (e.g. motilal-oswal-flexi-cap-fund -> Motilal Oswal Flexi Cap Fund)."""
    slug = url.rstrip("/").split("/")[-1] or ""
    words = slug.replace("-", " ").split()
    skip = {"direct", "growth", "option", "plan", "reinvestment", "payout", "inc", "dist", "cum", "cap", "wdrl"}
    parts = []
    for w in words:
        if w.isdigit() and len(w) >= 4:
            break
        if w.lower() in skip:
            continue
        parts.append(w)
    name = " ".join(parts).title()
    return name if len(parts) >= 2 else ""


def parse_fund_page(url: str, html: str) -> FundDocument | None:
    """
    Parse IndMoney fund page HTML into a FundDocument.
    Handles both server-rendered content and common HTML patterns.
    """
    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text(separator=" ", strip=True)
    full_text_nl = soup.get_text(separator="\n", strip=True)

    # Fund name: usually first h1 or title
    fund_name = ""
    h1 = soup.find("h1")
    if h1:
        fund_name = _text(h1)
    if not fund_name:
        fund_name = _re_first(full_text, r"SBI\s+[\w\s&]+Fund")
    if not fund_name:
        fund_name = _re_first(full_text, r"HDFC\s+[\w\s&]+Fund")
    if not fund_name:
        fund_name = _re_first(full_text, r"Motilal\s+Oswal\s+[\w\s&]+Fund")
    if not fund_name:
        fund_name = _re_first(full_text, r"Canara\s+Robeco\s+[\w\s&]+Fund")
    if not fund_name:
        fund_name = _re_first(full_text, r"ICICI\s+Prudential\s+[\w\s&]+Fund")
    if not fund_name:
        title = soup.find("title")
        if title:
            fund_name = _text(title).split("|")[0].split("-")[0].strip()
    name_from_url = _fund_name_from_url(url)
    if name_from_url and len(name_from_url.split()) >= 2:
        first_word = name_from_url.split()[0].lower()
        if not fund_name or first_word not in fund_name.lower():
            fund_name = name_from_url

    # Category / AMC from links or text
    category = _re_first_multiple(
        full_text,
        [
            (r"Large\s*&\s*Mid[- ]Cap", 0),
            (r"Large\s*and\s*Mid[- ]Cap", 0),
            (r"Large\s*Cap", 0),
            (r"Small\s*Cap", 0),
            (r"Mid\s*Cap", 0),
            (r"Midcap", 0),
            (r"Contra", 0),
            (r"Flexi\s*Cap", 0),
            (r"Focused", 0),
            (r"Fund\s+of\s+Fund", 0),
            (r"Index\s+Fund", 0),
            (r"ELSS", 0),
            (r"Midcap\s*150", 0),
            (r"Equity", 0),
        ],
    )
    if not category and "Large & Mid-Cap" in full_text:
        category = "Large & Mid-Cap"
    if not category and "ELSS" in full_text:
        category = "ELSS"
    if not category:
        category = "Equity"

    amc = "SBI Mutual Fund"
    if "canara" in url.lower() or "robeco" in url.lower() or ("Canara" in full_text and "Robeco" in full_text):
        amc = "Canara Robeco Mutual Fund"
    elif "motilal" in url.lower() or "Motilal" in full_text or "Oswal" in full_text:
        amc = "Motilal Oswal Mutual Fund"
    elif "hdfc" in url.lower() or ("HDFC" in full_text and "Mutual Fund" in full_text):
        amc = "HDFC Mutual Fund"
    elif "ICICI" in full_text and "Prudential" in full_text:
        amc = "ICICI Prudential Mutual Fund"

    # NAV, date, since inception
    nav = _re_first_multiple(
        full_text,
        [
            (r"₹\s*([\d,]+\.?\d*)\s*(?:▼|▲)", 1),
            (r"NAV[^\d]*([\d,]+\.?\d*)", 1),
        ],
    ).replace(",", "")
    nav_date = _re_first(full_text, r"NAV as on (\d{1,2}\s+\w+\s+\d{4})", 1)
    if not nav_date:
        nav_date = _re_first(full_text, r"as on\s*\(?(\d{1,2}[-/]\w+[-/]\d{2,4})\)?", 1)
    since_inception = _re_first_multiple(
        full_text,
        [
            (r"([\d.-]+%\s*/\s*per year)\s*Since Inception", 1),
            (r"Since Inception\s*([\d.-]+%)", 1),
        ],
    )

    # Overview block: Expense ratio, Benchmark, AUM, Min Lumpsum/SIP, Exit Load, Lock In, TurnOver, Risk
    expense_ratio = _re_first_multiple(
        full_text,
        [
            (r"Expense ratio\s*\|?\s*([\d.]+%)", 1),
            (r"Expense Ratio\s*([\d.]+%)", 1),
        ],
    )
    benchmark = _re_first_multiple(
        full_text,
        [
            (r"Benchmark\s*\|?\s*([^\n|]+?)(?:\s*AUM|\s*Exit|\s*Inception|$)", 1),
            (r"Nifty\s+[\w\s\d]+\s+TR\s+INR", 0),
            (r"BSE\s+[\w\s\d]+\s+(?:India\s+)?TR\s+INR", 0),
        ],
    ).strip()
    aum = _re_first_multiple(
        full_text,
        [
            (r"AUM\s*\|?\s*₹?\s*([\d,.]+\s*Cr)", 1),
            (r"₹\s*([\d,]+)\s*Cr\s*(?:\s*Inception|$)", 1),
        ],
    )
    inception_date = _re_first_multiple(
        full_text,
        [
            (r"Inception Date\s*\|?\s*([^\n|]+?)(?:\s*Min\s|$)", 1),
            (r"(\d{1,2}\s+\w+,\s+\d{4})\s*Min\s+Lumpsum", 1),
        ],
    ).strip()
    min_lumpsum_sip = _re_first_multiple(
        full_text,
        [
            (r"Min Lumpsum/SIP\s*\|?\s*([^\n|]+?)(?:\s*Exit|$)", 1),
            (r"₹([\d,]+)/₹([\d,]+)", 0),  # fallback: first ₹X/₹Y
        ],
    ).strip()
    if not min_lumpsum_sip and re.search(r"₹\s*[\d,]+\s*/\s*₹\s*[\d,]+", full_text):
        min_lumpsum_sip = re.search(r"₹\s*([\d,]+)\s*/\s*₹\s*([\d,]+)", full_text).group(0).strip()
    exit_load = _re_first_multiple(
        full_text,
        [
            (r"Exit Load\s*\|?\s*([^\n|]+?)(?:\s*Lock|$)", 1),
            (r"(\d+\.?\d*%)\s*(?:if redeemed|Lock)", 1),
        ],
    ).strip()
    lock_in = _re_first_multiple(
        full_text,
        [
            (r"Lock In\s*\|?\s*([^\n|]+?)(?:\s*TurnOver|$)", 1),
            (r"No Lock-in", 0),
            (r"3 years?", 0),
        ],
    ).strip()
    if not lock_in and "ELSS" in category:
        lock_in = "3 years"
    turnover = _re_first(full_text, r"TurnOver\s*\|?\s*([\d.]+%)", 1)
    riskometer = _re_first_multiple(
        full_text,
        [
            (r"Risk\s*\|?\s*([^\n|]+?)(?:\s*$|Risk meter)", 1),
            (r"(Very High Risk|High Risk|Moderately High|Moderate|Low)", 1),
        ],
    ).strip()

    # Investor snippet
    investor_snippet = _re_first(
        full_text,
        r"(\d+\s+people have invested\s+₹\s*[\d.]+\s*Cr in [^.]+\s+in the last three months)",
        1,
    )

    # Returns: "This Fund" row - 1M, 3M, 6M, 1Y, 3Y, 5Y (percentages)
    def extract_returns_row(text: str, row_name: str) -> dict[str, str]:
        # Look for pattern like "This Fund" then next tokens as percentages
        percents = re.findall(r"(-?\d+\.?\d*%)", text)
        # Often order is 1M, 3M, 6M, 1Y, 3Y, 5Y - we take first 6 percentages after "Period" or "This Fund"
        idx = text.find(row_name)
        if idx == -1:
            return {}
        after = text[idx : idx + 400]
        vals = re.findall(r"(-?\d+\.?\d*%)", after)
        labels = ["1m", "3m", "6m", "1y", "3y", "5y"]
        return dict(zip(labels, vals[:6])) if len(vals) >= 6 else {}

    fund_returns = extract_returns_row(full_text_nl, "This Fund")
    returns_1m = fund_returns.get("1m", "")
    returns_3m = fund_returns.get("3m", "")
    returns_6m = fund_returns.get("6m", "")
    returns_1y = fund_returns.get("1y", "")
    returns_3y = fund_returns.get("3y", "")
    returns_5y = fund_returns.get("5y", "")

    # SIP returns: look for "SIP" row, or "For SIP" / "SIP Returns" section with 6 percentages
    sip_returns = extract_returns_row(full_text_nl, "SIP")
    if not sip_returns:
        sip_returns = extract_returns_row(full_text_nl, "For SIP")
    if not sip_returns:
        sip_returns = extract_returns_row(full_text_nl, "SIP Returns")
    sip_1m = sip_returns.get("1m", "")
    sip_3m = sip_returns.get("3m", "")
    sip_6m = sip_returns.get("6m", "")
    sip_1y = sip_returns.get("1y", "")
    sip_3y = sip_returns.get("3y", "")
    sip_5y = sip_returns.get("5y", "")

    # About section
    about_el = soup.find("div", class_=re.compile("about|description", re.I)) or soup.find("section", id=re.compile("about", re.I))
    about_text = _text(about_el) if about_el else ""
    if not about_text:
        about_text = _re_first(full_text, r"About\s+SBI[\s\w]+Fund\s*([^.]+(?:\.[^.]+)*)", 1)[:1500]

    # FAQ section
    faq_headers = soup.find_all(["h2", "h3"], string=re.compile(r"FAQ|Frequently", re.I))
    faq_parts = []
    for h in faq_headers[:10]:
        next_el = h.find_next_sibling()
        if next_el:
            faq_parts.append(_text(next_el)[:500])
    faq_text = " ".join(faq_parts)[:2000] if faq_parts else ""

    return FundDocument(
        url=url,
        fund_name=fund_name or "SBI Fund",
        category=category,
        amc=amc,
        nav=nav or "",
        nav_date=nav_date or "",
        since_inception_return=since_inception or "",
        expense_ratio=expense_ratio or "",
        benchmark=benchmark or "",
        aum=aum or "",
        inception_date=inception_date or "",
        min_lumpsum_sip=min_lumpsum_sip or "",
        exit_load=exit_load or "",
        lock_in=lock_in or "",
        turnover=turnover or "",
        riskometer=riskometer or "",
        investor_snippet=investor_snippet or "",
        returns_lumpsum_1m=returns_1m,
        returns_lumpsum_3m=returns_3m,
        returns_lumpsum_6m=returns_6m,
        returns_lumpsum_1y=returns_1y,
        returns_lumpsum_3y=returns_3y,
        returns_lumpsum_5y=returns_5y,
        returns_sip_1m=sip_1m,
        returns_sip_3m=sip_3m,
        returns_sip_6m=sip_6m,
        returns_sip_1y=sip_1y,
        returns_sip_3y=sip_3y,
        returns_sip_5y=sip_5y,
        about_text=about_text,
        faq_text=faq_text,
    )
