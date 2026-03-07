"""Phase 1: RAG retrieval and answer generation. Every answer includes source URL(s)."""

from .config import TOP_K_RETRIEVAL
from .embed_store import query_collection


def retrieve(query: str, top_k: int = TOP_K_RETRIEVAL, where: dict | None = None) -> list[tuple[str, dict, float]]:
    """Retrieve top-k chunks for a query. Returns (document, metadata, distance). Metadata has source_url."""
    return query_collection(query, n_results=top_k, where=where)


def answer_from_chunks(query: str, chunks: list[tuple[str, dict, float]]) -> tuple[str, list[dict]]:
    """
    Build an answer from retrieved chunks. Returns (answer_text, sources).
    sources is a list of dicts with "url" (source URL) and "fund_name" so every answer
    returns the correct URL(s) from which the information came.
    """
    if not chunks:
        return (
            "I couldn't find relevant information for that question in the current data. "
            "Please try rephrasing or ask about mutual funds (expense ratio, exit load, minimum SIP, benchmark, riskometer, ELSS lock-in, or capital gains statement download).",
            [],
        )
    doc, meta, _ = chunks[0]
    sources = []
    url = meta.get("source_url", "").strip()
    fund = meta.get("fund_name", "").strip()
    if url or fund:
        sources.append({"url": url or "N/A", "fund_name": fund})

    answer = doc.strip()
    if len(answer) > 1500:
        answer = answer[:1500].rsplit("\n", 1)[0] + "\n\n[Content truncated. See source URL for full details.]"

    for d, m, _ in chunks[1:5]:
        u = (m.get("source_url") or "").strip()
        f = (m.get("fund_name") or "").strip()
        if (u or f) and not any(s.get("url") == (u or "N/A") for s in sources):
            sources.append({"url": u or "N/A", "fund_name": f})

    return answer, sources


def ask(query: str, top_k: int = TOP_K_RETRIEVAL) -> tuple[str, list[dict]]:
    """Retrieve and return (answer, sources). sources contain the URL for each piece of information."""
    chunks = retrieve(query, top_k=top_k)
    return answer_from_chunks(query, chunks)
