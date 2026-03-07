"""
Phase 2: Chat backend – FastAPI app.
Implements Phase 2 architecture: POST /chat, GET /health; RAG pipeline + LLM; optional session_id and source snippets.
"""
# Use pysqlite3 so Chroma gets SQLite >= 3.35 on systems with older bundled sqlite3 (e.g. macOS)
try:
    import pysqlite3
    import sys
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import asyncio
import hashlib
import os
import time
from pathlib import Path

# Load .env from project root (for GROQ_API_KEY, PHASE2_HOST, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from phase2.rag_service import chat
from phase6 import log_qa, record_feedback

app = FastAPI(
    title="IndMoney RAG Chat API",
    description="Chat API for mutual fund Q&A with source citations.",
    version="1.0",
)

# CORS so frontend (same host or separate) can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: serve frontend from phase2/frontend when hitting /
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


@app.on_event("startup")
def _log_frontend_path():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        print(f"Frontend: serving UI at / from {index}")
    else:
        print(f"Frontend: WARNING - index not found at {index} (GET / will return 404)")

# Phase 5: in-memory response cache (cleared on refresh-complete); max 500 entries
_chat_cache: dict[str, dict] = {}
_CACHE_MAX = 500
# Phase 5: rate limit 60 requests/min per IP
_rate_limit: dict[str, list[float]] = {}
_RATE_LIMIT_N = 60
_RATE_LIMIT_WINDOW = 60.0


def _cache_key(msg: str) -> str:
    return hashlib.sha256(msg.strip().lower().encode()).hexdigest()


def _check_rate_limit(ip: str) -> bool:
    now = time.monotonic()
    if ip not in _rate_limit:
        _rate_limit[ip] = []
    times = _rate_limit[ip]
    times.append(now)
    times[:] = [t for t in times if now - t < _RATE_LIMIT_WINDOW]
    return len(times) <= _RATE_LIMIT_N


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User question")
    session_id: str | None = Field(None, max_length=256, description="Optional conversation/session ID for future multi-turn")


class FeedbackRequest(BaseModel):
    """Phase 6: thumbs up/down or report error."""
    question: str = Field(..., min_length=1, max_length=2000)
    rating: str = Field(..., description="up | down | report")
    session_id: str | None = Field(None, max_length=256)
    comment: str | None = Field(None, max_length=500)


class SourceItem(BaseModel):
    url: str
    title: str
    snippet: str | None = Field(None, description="Optional chunk snippet for citation")


class ScrapedFundItem(BaseModel):
    """Structured scraped data for one fund: link plus key fields from scraped pages."""
    link: str = Field(..., description="Fund page URL")
    fund_name: str | None = None
    amc: str | None = None
    category: str | None = None
    expense_ratio: str | None = None
    benchmark: str | None = None
    riskometer: str | None = None
    lock_in: str | None = None
    min_sip: str | None = None
    nav: str | None = None
    nav_date: str | None = None
    exit_load: str | None = None
    aum: str | None = None

    class Config:
        extra = "allow"  # allow any extra keys from metadata


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    scraped_data: list[ScrapedFundItem] = Field(default_factory=list, description="Scraped fund data with link per fund")
    session_id: str | None = Field(None, description="Echo of request session_id if provided")


@app.get("/health")
def health():
    """Readiness for load balancer / scheduler."""
    return {"status": "ok"}


@app.get("/meta")
def get_meta():
    """Index metadata for UI (e.g. Data last updated). Reads from data/structured/courses.json."""
    try:
        from phase5.metadata import get_last_updated
        last_updated = get_last_updated()
        return {"last_updated": last_updated}
    except Exception:
        return {"last_updated": None}


@app.get("/metrics")
def metrics():
    """Phase 5: basic metrics (cache size)."""
    return {"chat_cache_size": len(_chat_cache), "rate_limit_ips": len(_rate_limit)}


@app.post("/feedback")
def post_feedback(body: FeedbackRequest):
    """Phase 6: record thumbs up/down or report error for improvement."""
    try:
        record_feedback(body.question, body.rating, body.session_id, body.comment)
        return Response(status_code=204)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save feedback.")


@app.post("/admin/refresh-complete")
def admin_refresh_complete():
    """
    Called by Phase 3 after a successful data refresh. Clears response cache so new data is served.
    """
    global _chat_cache
    _chat_cache.clear()
    return Response(status_code=204)


@app.post("/chat", response_model=ChatResponse)
async def post_chat(request: Request, body: ChatRequest):
    """
    Send a message and get an answer with source URLs (and optional snippets).
    Phase 5: response cache, rate limiting (60/min per IP).
    """
    # Rate limit
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Try again in a minute.")
    # Cache lookup
    key = _cache_key(body.message)
    if key in _chat_cache:
        r = _chat_cache[key]
        return ChatResponse(
            answer=r["answer"],
            sources=[SourceItem(url=s["url"], title=s["title"], snippet=s.get("snippet")) for s in r["sources"]],
            scraped_data=[ScrapedFundItem(**d) for d in r.get("scraped_data", [])],
            session_id=body.session_id,
        )
    try:
        result = await asyncio.to_thread(chat, body.message)
        answer = result["answer"]
        log_qa(body.message, (answer or "")[:300], body.session_id)
        resp = ChatResponse(
            answer=answer,
            sources=[
                SourceItem(
                    url=s["url"],
                    title=s["title"],
                    snippet=s.get("snippet"),
                )
                for s in result["sources"]
            ],
            scraped_data=[ScrapedFundItem(**d) for d in result.get("scraped_data", [])],
            session_id=body.session_id,
        )
        if len(_chat_cache) < _CACHE_MAX:
            _chat_cache[key] = {
                "answer": result["answer"],
                "sources": result["sources"],
                "scraped_data": result.get("scraped_data", []),
            }
        return resp
    except Exception:
        raise HTTPException(status_code=500, detail="Please try again.")


# Serve frontend: index.html at / and static assets from /assets if present
@app.get("/")
def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index, media_type="text/html")
    raise HTTPException(
        status_code=404,
        detail=f"Frontend not found at {index}. Run the server from the project root.",
    )


@app.get("/assets/{rest:path}")
def serve_assets(rest: str):
    f = FRONTEND_DIR / "assets" / rest
    if f.exists() and f.is_file():
        return FileResponse(f)
    raise HTTPException(status_code=404, detail="Not found")


def main():
    import uvicorn
    try:
        from phase2.config import PHASE2_HOST, PHASE2_PORT
    except Exception:
        PHASE2_HOST = os.environ.get("PHASE2_HOST", "0.0.0.0")
        PHASE2_PORT = int(os.environ.get("PHASE2_PORT", "8000"))
    uvicorn.run("phase2.app:app", host=PHASE2_HOST, port=PHASE2_PORT, reload=True)


if __name__ == "__main__":
    main()
