"""Phase 1: Chunk fund documents and static content for RAG."""

import json
from pathlib import Path

from .parser import FundDocument

# Static content: capital gains statement download (IndMoney app)
CAPITAL_GAINS_STATEMENT_CHUNK = """How to download capital gains statement for mutual funds on IndMoney:
1. Log in to the IndMoney app.
2. Tap "More" on the bottom right of the homepage.
3. Scroll to "Taxation & Report" and select "Mutual Fund".
4. Choose the financial year (e.g. FY 2022-23).
5. Tap "Download" to get your capital gains report.

The capital gains statement (P&L statement) shows all mutual fund transactions in the financial year, including short-term and long-term capital gains. You can use it for ITR filing.
Source: IndMoney app (Taxation & Report)."""


def chunk_fund_document(doc: FundDocument) -> list[tuple[str, dict]]:
    """
    Split a FundDocument into one or more (text, metadata) chunks.
    Each chunk has source_url in metadata for correct URL in answers.
    """
    text = doc.to_document_text()
    meta = doc.to_metadata()
    meta["page_type"] = "fund_page"
    chunks = []

    if text:
        chunks.append((text, meta))

    if doc.faq_text and len(doc.faq_text) > 200:
        faq_meta = {**meta, "section": "faq"}
        chunks.append((f"FAQs for {doc.fund_name}:\n{doc.faq_text}", faq_meta))

    return chunks


def get_static_chunks() -> list[tuple[str, dict]]:
    """Chunks for static/curated content (e.g. capital gains download)."""
    return [
        (
            CAPITAL_GAINS_STATEMENT_CHUNK,
            {
                "source_url": "https://www.indmoney.com/",
                "fund_name": "",
                "amc": "",
                "category": "",
                "page_type": "static",
                "section": "capital_gains_statement",
            },
        ),
    ]


def build_all_chunks(fund_documents: list[FundDocument]) -> list[tuple[str, dict]]:
    """Build list of (text, metadata) for all fund docs plus static chunks."""
    out = []
    for doc in fund_documents:
        out.extend(chunk_fund_document(doc))
    out.extend(get_static_chunks())
    return out


def build_chunks_from_scraped_json(json_path=None) -> list[tuple[str, dict]]:
    """
    Build RAG chunks from data/scraped_funds.json. Use this so that the vector store
    (and thus every answer’s source URL) is based on the updated scraped data file.
    Each chunk includes source_url in metadata.
    """
    from config import SCRAPED_FUNDS_JSON

    path = Path(json_path) if json_path else Path(SCRAPED_FUNDS_JSON)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    documents = [FundDocument.from_dict(d) for d in data if isinstance(d, dict) and d.get("url")]
    return build_all_chunks(documents)
