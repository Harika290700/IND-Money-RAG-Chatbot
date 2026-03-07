"""Phase 4: Chunk fund documents (Phase 1) and generic blog/help pages."""

import re
from typing import Any

from .config import CHUNK_OVERLAP, CHUNK_SIZE
from .parser import GenericPage


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into chunks by size with overlap. Tries to break at sentence/paragraph boundaries."""
    if not text or len(text) <= chunk_size:
        return [text] if text and text.strip() else []
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # Prefer break at newline or sentence end
        segment = text[start:end]
        break_at = max(
            segment.rfind("\n\n"),
            segment.rfind("\n"),
            max((m.start() for m in re.finditer(r"[.!?]\s+", segment), default=-1)),
        )
        if break_at > chunk_size // 2:
            end = start + break_at + 1
        chunks.append(text[start:end].strip())
        start = end - overlap
        if start <= 0:
            start = end
    return [c for c in chunks if c]


def chunk_generic_page(page: GenericPage) -> list[tuple[str, dict[str, Any]]]:
    """Split a generic page into (text, metadata) chunks. Metadata has source_url, page_type, title."""
    chunks = chunk_text(page.text, CHUNK_SIZE, CHUNK_OVERLAP)
    out = []
    for i, c in enumerate(chunks):
        meta = {
            "source_url": page.url,
            "fund_name": page.title,
            "page_type": page.page_type,
            "section": f"chunk_{i}",
        }
        out.append((c, meta))
    return out


def build_fund_chunks(fund_documents: list) -> list[tuple[str, dict]]:
    """Build chunks from fund documents using Phase 1 chunking (no static chunks to avoid duplicate)."""
    from phase1.chunking import chunk_fund_document
    out = []
    for doc in fund_documents:
        out.extend(chunk_fund_document(doc))
    return out


def build_generic_chunks(pages: list[GenericPage]) -> list[tuple[str, dict]]:
    """Build chunks from generic (blog/help) pages."""
    out = []
    for p in pages:
        out.extend(chunk_generic_page(p))
    return out
