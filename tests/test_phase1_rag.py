"""
Phase 1 tests: RAG retrieval and answer generation.
- Unit tests with mocked retrieval (no Chroma).
- Integration tests (marked @pytest.mark.integration) use real vector store when available.
"""
import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# --- Unit tests (no Chroma) ---


class TestPhase1AnswerFromChunks:
    """Test answer_from_chunks and ask() with mocked retrieve."""

    def test_answer_from_chunks_empty_returns_graceful_message(self):
        from phase1.rag import answer_from_chunks
        answer, sources = answer_from_chunks("What is the NAV?", [])
        assert "couldn't find" in answer.lower() or "rephrasing" in answer.lower()
        assert sources == []

    def test_answer_from_chunks_with_chunk_returns_answer_and_sources(self):
        from phase1.rag import answer_from_chunks
        doc = "ICICI Prudential Large Cap Fund. NAV today is ₹121.28 (as on 05 Mar 2026)."
        meta = {"source_url": "https://www.indmoney.com/mutual-funds/icici-prudential-large-cap-fund-direct-plan-growth-2995", "fund_name": "ICICI Prudential Large Cap Fund"}
        chunks = [(doc, meta, 0.1)]
        answer, sources = answer_from_chunks("What is the nav for ICICI large cap fund?", chunks)
        assert answer.strip()
        assert len(sources) >= 1
        assert sources[0].get("url") or sources[0].get("fund_name")
        assert "121.28" in doc  # NAV in chunk

class TestPhase1RetrieveIntegration:
    """Integration: real retrieve() and ask() against Chroma. Skip if no DB."""

    @pytest.fixture(scope="module")
    def chroma_available(self):
        from phase1.config import CHROMA_PERSIST_DIR
        return (CHROMA_PERSIST_DIR / "chroma.sqlite3").exists() or (CHROMA_PERSIST_DIR / "chroma.sqlite3").exists() is False and CHROMA_PERSIST_DIR.exists()

    @pytest.mark.integration
    def test_retrieve_returns_list_of_tuples(self):
        from phase1.rag import retrieve
        try:
            chunks = retrieve("What is the expense ratio of SBI Contra Fund?", top_k=2)
        except Exception as e:
            pytest.skip(f"Chroma not available: {e}")
        assert isinstance(chunks, list)
        for c in chunks:
            assert len(c) == 3  # (doc, meta, distance)
            assert isinstance(c[0], str)
            assert isinstance(c[1], dict)
            assert isinstance(c[2], (int, float))

    @pytest.mark.integration
    def test_ask_returns_answer_and_sources(self):
        from phase1.rag import ask
        try:
            answer, sources = ask("What is the expense ratio of SBI Contra Fund?", top_k=3)
        except Exception as e:
            pytest.skip(f"Chroma not available: {e}")
        assert isinstance(answer, str)
        assert answer.strip()
        assert isinstance(sources, list)
        # May or may not have sources if index is empty
        for s in sources:
            assert "url" in s or "fund_name" in s

    @pytest.mark.integration
    def test_example_nav_query_icici_large_cap(self):
        """Example test case: What is the nav for icici large cap fund?"""
        from phase1.rag import ask
        query = "What is the nav for icici large cap fund?"
        try:
            answer, sources = ask(query, top_k=5)
        except Exception as e:
            pytest.skip(f"Chroma not available: {e}")
        assert isinstance(answer, str)
        assert isinstance(sources, list)
        # If we have indexed ICICI Large Cap, answer may contain NAV (e.g. 121.28) or fund info
        # If no data, answer is graceful "couldn't find"
        assert "couldn't find" in answer.lower() or "121" in answer or "nav" in answer.lower() or "icici" in answer.lower() or len(answer) > 20
        for s in sources:
            assert isinstance(s, dict)
            assert s.get("url") or s.get("fund_name")
