"""
Phase 2: RAG + Groq LLM service.
Retrieves chunks from Phase 1 vector store, generates answer via Groq using only that context.
Enforces: answer only from embeddings; no personal information.
Architecture: retrieve → LLM; timeouts and graceful error handling.
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

# Ensure project root is on path when running as python -m phase2.app or from phase2
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env from project root so GROQ_API_KEY and GROQ_MODEL are available
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from phase1.rag import retrieve

try:
    from phase2.config import (
        PHASE2_TOP_K,
        LLM_TIMEOUT_SEC,
        GROQ_API_KEY as _ENV_GROQ_KEY,
        GROQ_MODEL as _ENV_GROQ_MODEL,
        SOURCE_SNIPPET_MAX_CHARS,
    )
except Exception:
    PHASE2_TOP_K = 5
    LLM_TIMEOUT_SEC = 30
    _ENV_GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
    _ENV_GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant").strip()
    SOURCE_SNIPPET_MAX_CHARS = 200

# Optional Groq; if not configured, we fall back to chunk-only response
try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False
    Groq = None

SYSTEM_PROMPT = """You are a helpful assistant for IndMoney mutual fund information. Answer **only** from the provided context (scraped fund data). Use a clear, full-sentence style. Examples: for exit load say "The exit load for [fund] is X.X% if redeemed in 1 year."; for NAV say "The NAV of [fund] is ₹X.XX as on [date]."; for expense ratio say "The expense ratio for [fund] is X.XX%."; for minimum SIP say "The minimum SIP for [fund] is ₹X."; for risk say "The fund is [High/Medium/Low] Risk." Do not include the word "Source" or a URL in your answer—the link is shown separately. Do not list extra details. Do not use your own knowledge. If the context does not contain the answer, say so. Do not answer questions about personal information."""

# Heuristic: questions asking for or about personal/private user data are out of scope
PERSONAL_INFO_PATTERNS = re.compile(
    r"\b(my|your)\s+(account|portfolio|email|phone|number|address|name|details|investment|holdings|aadhaar|pan|kyc)\b"
    r"|\b(account\s+number|phone\s+number|email\s+address)\b"
    r"|\b(who\s+am\s+i|my\s+identity|my\s+contact)\b",
    re.IGNORECASE,
)

# Only answer questions that relate to our scraped data (mutual funds: NAV, expense, exit load, etc.)
ALLOWED_TOPIC_KEYWORDS = re.compile(
    r"\b(nav|net\s+asset|expense\s+ratio|ter|exit\s+load|minimum\s+sip|min\s+sip|sip|"
    r"lumpsum|lump\s+sum|riskometer|risk|benchmark|lock[- ]?in|elss|"
    r"mutual\s+fund|fund\s+name|scheme|amc|category|aum|"
    r"sbi|icici|contra|large\s+cap|midcap|small\s+cap|flexi|index\s+fund|"
    r"expense|ratio|returns?|inception)\b",
    re.IGNORECASE,
)


def is_personal_info_query(message: str) -> bool:
    """Return True if the query appears to ask for or about personal information (out of scope)."""
    if not (message or message.strip()):
        return False
    return bool(PERSONAL_INFO_PATTERNS.search(message.strip()))


def is_relevant_to_scraped_data(message: str) -> bool:
    """Return True if the question is about mutual fund data we have (NAV, expense ratio, funds, etc.)."""
    if not (message or message.strip()):
        return False
    return bool(ALLOWED_TOPIC_KEYWORDS.search(message.strip()))


def _strip_source_from_answer(answer: str) -> str:
    """Remove any 'Source: ...' or URL-only lines so the link is only shown via the sources field."""
    if not answer or not isinstance(answer, str):
        return answer or ""
    kept = []
    for line in answer.split("\n"):
        s = line.strip()
        if not s:
            kept.append(line)
            continue
        lower = s.lower()
        if "source:" in lower or "source :" in lower or s.startswith("http://") or s.startswith("https://") or "indmoney.com" in lower and ("http" in lower or "www." in lower):
            continue
        kept.append(line)
    return "\n".join(kept).strip() or ""


def _is_exit_load_question(message: str) -> bool:
    """True if the user is asking only about exit load."""
    if not message or not isinstance(message, str):
        return False
    q = message.lower().strip()
    if "exit load" not in q and "exitload" not in q:
        return False
    return True


def _build_context(chunks: list[tuple[str, dict, float]], message: str | None = None) -> str:
    """Build a single context string from retrieved chunks for the LLM.
    When message is an exit-load question, context contains only fund name and exit load %."""
    parts = []
    exit_load_only = message and _is_exit_load_question(message)
    for i, (doc, meta, _) in enumerate(chunks, 1):
        url = (meta.get("source_url") or "").strip()
        fund = (meta.get("fund_name") or "").strip()
        header = f"[{i}]"
        if fund:
            header += f" ({fund})"
        # Do not put URL in context so the LLM does not echo "Source: url" in the answer
        if exit_load_only:
            raw_exit = meta.get("exit_load") or ""
            pct = _extract_exit_load_percentage(raw_exit)
            body = f"Exit load: {pct}" if pct else doc.strip()
        else:
            body = doc.strip()
        parts.append(f"{header}\n{body}")
    return "\n\n".join(parts)


# Scraped-data fields we pass through from chunk metadata to the API (for "scraped data + link" response).
SCRAPED_DATA_KEYS = (
    "source_url", "fund_name", "amc", "category", "expense_ratio", "benchmark",
    "riskometer", "lock_in", "min_sip", "nav", "nav_date", "exit_load", "aum",
)


def _sources_from_chunks(
    chunks: list[tuple[str, dict, float]],
    include_snippet: bool = True,
    snippet_max_chars: int = 200,
) -> list[dict[str, Any]]:
    """Extract unique sources (url, title, optional snippet) from chunk metadata."""
    seen_urls: set[str] = set()
    out = []
    for doc, meta, _ in chunks:
        url = (meta.get("source_url") or "").strip()
        fund = (meta.get("fund_name") or "").strip()
        url = url or "N/A"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        title = fund or url
        item: dict[str, Any] = {"url": url, "title": title}
        if include_snippet and snippet_max_chars > 0 and doc:
            snip = (doc or "").strip().replace("\n", " ")[:snippet_max_chars]
            if len((doc or "").strip()) > snippet_max_chars:
                snip += "…"
            item["snippet"] = snip
        out.append(item)
    return out


def _scraped_data_from_chunks(chunks: list[tuple[str, dict, float]]) -> list[dict[str, Any]]:
    """Build list of scraped-data items (one per unique source_url) with link and all stored fields."""
    seen_urls: set[str] = set()
    out = []
    for _doc, meta, _ in chunks:
        url = (meta.get("source_url") or "").strip()
        url = url or "N/A"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        row: dict[str, Any] = {"link": url, "fund_name": (meta.get("fund_name") or "").strip() or None}
        for k in SCRAPED_DATA_KEYS:
            if k == "source_url":
                continue
            v = meta.get(k)
            if v is not None and str(v).strip():
                row[k] = str(v).strip()
        out.append(row)
    return out


def _fallback_chunks_from_scraped_json(message: str, top_k: int = 5) -> list[tuple[str, dict, float]]:
    """
    When Chroma is unavailable or returns no results, load data/scraped_funds.json and return
    chunk-like (doc, meta, distance) for funds that match the query (simple keyword match).
    Ensures the app can always answer from scraped data.
    """
    import json
    path = _ROOT / "data" / "scraped_funds.json"
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            funds = json.load(f)
    except Exception:
        return []
    if not isinstance(funds, list):
        return []
    q_lower = (message or "").lower().strip()
    q_words = [w for w in q_lower.split() if len(w) > 1]
    out = []
    for fund in funds:
        if not isinstance(fund, dict):
            continue
        name = (fund.get("fund_name") or "").lower()
        url = (fund.get("url") or "").strip()
        text_parts = [
            name,
            (fund.get("category") or "").lower(),
            (fund.get("amc") or "").lower(),
            (fund.get("about_text") or "").lower(),
            (fund.get("faq_text") or "").lower(),
        ]
        search_text = " ".join(text_parts)
        score = 0
        for w in q_words:
            if w in name:
                score += 3
            if w in search_text:
                score += 1
        if not q_words or score > 0:
            doc_lines = [
                f"Fund: {fund.get('fund_name', '')}",
                f"NAV: {fund.get('nav', '')} (as on {fund.get('nav_date', '')})",
                f"Expense ratio: {fund.get('expense_ratio', '')}",
                f"Min SIP/Lumpsum: {fund.get('min_lumpsum_sip', '')}",
                f"Exit load: {fund.get('exit_load', '')}",
                f"Riskometer: {fund.get('riskometer', '')}",
                f"Category: {fund.get('category', '')}",
                f"Benchmark: {fund.get('benchmark', '')}",
                f"Lock-in: {fund.get('lock_in', '')}",
                f"AUM: {fund.get('aum', '')}",
            ]
            doc = "\n".join(doc_lines)
            meta = {
                "source_url": url,
                "fund_name": fund.get("fund_name"),
                "amc": fund.get("amc"),
                "category": fund.get("category"),
                "expense_ratio": fund.get("expense_ratio"),
                "benchmark": fund.get("benchmark"),
                "riskometer": fund.get("riskometer"),
                "lock_in": fund.get("lock_in"),
                "min_sip": fund.get("min_lumpsum_sip"),
                "nav": fund.get("nav"),
                "nav_date": fund.get("nav_date"),
                "exit_load": fund.get("exit_load"),
                "aum": fund.get("aum"),
            }
            out.append((doc, meta, -score))
    out.sort(key=lambda x: x[2])
    return [(doc, meta, 0.0) for doc, meta, _ in out[:top_k]]


def _topic_keys_from_question(question: str) -> list[str]:
    """Return which scraped-data keys are relevant to the question (e.g. nav for 'what is nav')."""
    q = (question or "").lower()
    if "nav" in q or "net asset" in q:
        return ["nav", "nav_date"]
    if "expense" in q or "ter" in q:
        return ["expense_ratio"]
    if "exit load" in q or "exitload" in q:
        return ["exit_load"]
    if "min" in q and ("sip" in q or "lump" in q or "invest" in q):
        return ["min_sip"]
    if "risk" in q or "riskometer" in q:
        return ["riskometer"]
    if "benchmark" in q:
        return ["benchmark"]
    if "lock" in q or "lock-in" in q or "elss" in q:
        return ["lock_in"]
    if "aum" in q or "assets under" in q:
        return ["aum"]
    if "category" in q:
        return ["category"]
    if "amc" in q or "fund house" in q:
        return ["amc"]
    return ["nav", "nav_date", "expense_ratio"]


def _extract_exit_load_percentage(exit_load_val: str) -> str:
    """Extract only the exit load percentage from verbose text (e.g. 'Exit Load 1.0%' -> '1.0%')."""
    if not exit_load_val or not isinstance(exit_load_val, str):
        return ""
    m = re.search(r"Exit Load\s*([\d.]+%?)", exit_load_val, re.IGNORECASE)
    if m:
        pct = m.group(1).strip()
        return pct if "%" in pct else pct + "%"
    m = re.search(r"([\d.]+)\s*%", exit_load_val)
    if m:
        return m.group(0).strip()
    return exit_load_val.strip()


def _normalize_risk_label(riskometer_val: str) -> str:
    """Map riskometer text to High Risk, Medium Risk, or Low Risk for answers."""
    if not riskometer_val:
        return "Unknown"
    v = riskometer_val.strip().lower()
    if "low" in v and "high" not in v:
        return "Low Risk"
    if "moderate" in v or "medium" in v or "moderately" in v:
        return "Medium Risk"
    if "very high" in v or "high" in v:
        return "High Risk"
    if "low" in v:
        return "Low Risk"
    return "Medium Risk"


def _answer_from_scraped_data(
    chunks: list[tuple[str, dict, float]],
    scraped_data: list[dict[str, Any]],
    question: str,
) -> str:
    """Build one full-sentence answer per fund (e.g. 'The exit load for X is 1.0% if redeemed in 1 year.'). No Source text—link is sent separately."""
    if not scraped_data:
        return "I couldn't find relevant information for that question in the current data."
    keys_to_show = _topic_keys_from_question(question)
    parts = []
    for row in scraped_data[:3]:
        fund = row.get("fund_name") or "Fund"
        sentence = None
        if "exit_load" in keys_to_show:
            val = row.get("exit_load")
            pct = _extract_exit_load_percentage(val or "") if val else ""
            if pct:
                sentence = f"The exit load for {fund} is {pct} if redeemed in 1 year."
            elif val:
                sentence = f"The exit load for {fund} is {val}."
        elif "riskometer" in keys_to_show:
            val = row.get("riskometer")
            if val:
                sentence = f"The fund is {_normalize_risk_label(val)}."
        elif "nav" in keys_to_show or "nav_date" in keys_to_show:
            nav = (row.get("nav") or "").strip()
            nav_date = (row.get("nav_date") or "").strip()
            if nav:
                sentence = f"The NAV of {fund} is ₹{nav}" + (f" as on {nav_date}." if nav_date else ".")
            elif nav_date:
                sentence = f"The NAV date for {fund} is {nav_date}."
        elif "expense_ratio" in keys_to_show:
            val = row.get("expense_ratio")
            if val:
                sentence = f"The expense ratio for {fund} is {val}."
        elif "min_sip" in keys_to_show:
            val = row.get("min_sip")
            if val:
                sentence = f"The minimum SIP for {fund} is {val}."
        elif "lock_in" in keys_to_show:
            val = row.get("lock_in")
            if val:
                sentence = f"The lock-in for {fund} is {val}."
        elif "benchmark" in keys_to_show:
            val = row.get("benchmark")
            if val:
                sentence = f"The benchmark for {fund} is {val}."
        elif "aum" in keys_to_show:
            val = row.get("aum")
            if val:
                sentence = f"The AUM of {fund} is {val}."
        elif "category" in keys_to_show:
            val = row.get("category")
            if val:
                sentence = f"The category of {fund} is {val}."
        elif "amc" in keys_to_show:
            val = row.get("amc")
            if val:
                sentence = f"The AMC for {fund} is {val}."
        if sentence:
            parts.append(sentence)
    return "\n".join(parts) if parts else "I couldn't find relevant information for that question in the current data."


def _generate_with_groq(context: str, question: str, timeout_sec: int = 30) -> str | None:
    """Call Groq to generate answer from context + question. Returns None if disabled, timeout, or error."""
    api_key = _ENV_GROQ_KEY or os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key or not _GROQ_AVAILABLE or Groq is None:
        return None
    model = _ENV_GROQ_MODEL or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
    user_content = f"Context:\n{context}\n\nQuestion: {question}"

    def _call() -> str | None:
        try:
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                model=model,
                temperature=0.2,
                max_tokens=384,
            )
            text = completion.choices[0].message.content
            return (text or "").strip() or None
        except Exception:
            return None

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_call)
            return fut.result(timeout=timeout_sec)
    except (FuturesTimeoutError, Exception):
        return None


def chat(
    message: str,
    top_k: int | None = None,
    include_snippets: bool = True,
) -> dict[str, Any]:
    """
    Process one user message: guardrails → retrieve → LLM (Groq) → answer + sources.
    Returns {"answer": str, "sources": [{"url", "title", optional "snippet"}]}.
    Timeouts and LLM failures yield a graceful "Please try again." style response.
    """
    message = (message or "").strip()
    if not message:
        return {
            "answer": "Please ask a question about mutual funds (e.g. expense ratio, minimum SIP, exit load, ELSS lock-in, or capital gains statement).",
            "sources": [],
            "scraped_data": [],
        }

    # Out-of-scope: personal information
    if is_personal_info_query(message):
        return {
            "answer": "I don't handle personal information. I can only help with factual mutual fund information from our indexed content (e.g. fund details, expense ratio, exit load, minimum SIP, ELSS lock-in, capital gains statement download).",
            "sources": [],
            "scraped_data": [],
        }

    # Only answer questions about our scraped data (mutual funds)
    if not is_relevant_to_scraped_data(message):
        return {
            "answer": "I can provide only factual information related to SBI, HDFC, ICICI, Canara Robeco, Motilal Oswal Funds.",
            "sources": [],
            "scraped_data": [],
        }

    k = top_k if top_k is not None else PHASE2_TOP_K
    try:
        chunks = retrieve(message, top_k=k)
    except Exception:
        chunks = []
    if not chunks:
        chunks = _fallback_chunks_from_scraped_json(message, top_k=k)
    if not chunks:
        return {
            "answer": "I couldn't find relevant information for that question in the current data. Please try rephrasing or ask about mutual funds (expense ratio, exit load, minimum SIP, benchmark, riskometer, ELSS lock-in, or capital gains statement download). If you just set up the app, ensure data/scraped_funds.json exists or run: python -m phase1.run_pipeline --from-json",
            "sources": [],
            "scraped_data": [],
        }

    snippet_max = SOURCE_SNIPPET_MAX_CHARS if include_snippets else 0
    sources = _sources_from_chunks(chunks, include_snippet=include_snippets, snippet_max_chars=snippet_max)
    sources = sources[:1]
    scraped_data = _scraped_data_from_chunks(chunks)[:1]
    context = _build_context(chunks, message)

    # Try LLM first when available; otherwise answer directly from scraped data
    answer = _generate_with_groq(context, message, timeout_sec=LLM_TIMEOUT_SEC)
    if answer:
        answer = _strip_source_from_answer(answer)

    if not answer and scraped_data:
        # Fallback 1: concise answer from scraped_data (only what was asked, e.g. NAV only)
        answer = _answer_from_scraped_data(chunks, scraped_data, message)
    if not answer:
        # Fallback 2: use first chunk text (no Source in answer—link is in sources)
        try:
            doc, meta, _ = chunks[0]
            if _is_exit_load_question(message):
                fund = (meta.get("fund_name") or "Fund").strip()
                pct = _extract_exit_load_percentage(meta.get("exit_load") or "")
                answer = f"The exit load for {fund} is {pct} if redeemed in 1 year." if pct else (doc or "").strip()
            else:
                answer = (doc or "").strip()
            if answer and len(answer) > 500 and not _is_exit_load_question(message):
                answer = answer[:500].rsplit("\n", 1)[0]
        except Exception:
            answer = ""
    if not answer:
        answer = "I couldn't generate a response right now. Please try again."
    else:
        answer = _strip_source_from_answer(answer)

    return {"answer": answer, "sources": sources, "scraped_data": scraped_data}
