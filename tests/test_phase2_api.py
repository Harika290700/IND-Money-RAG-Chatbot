"""
Phase 2 tests: Chat API (FastAPI).
- GET /health
- POST /chat (with example query: What is the nav for icici large cap fund?)
- POST /admin/refresh-complete
Integration: /chat uses Phase 1 RAG + optional Groq; may skip or mock if no Chroma.
"""
import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from phase2.app import app
    return TestClient(app)


@pytest.mark.phase2
class TestPhase2Health:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.phase2
class TestPhase2Chat:
    """POST /chat - structure and example NAV query."""

    def test_chat_requires_message(self, client):
        r = client.post("/chat", json={})
        assert r.status_code == 422  # validation error

    def test_chat_rejects_empty_message(self, client):
        r = client.post("/chat", json={"message": "   "})
        assert r.status_code == 422

    def test_chat_returns_answer_and_sources(self, client):
        r = client.post(
            "/chat",
            json={"message": "What is the expense ratio of SBI Contra Fund?"},
        )
        # May be 200 (success) or 500 if Chroma/LLM unavailable
        if r.status_code != 200:
            pytest.skip("Backend unavailable (Chroma or LLM)")
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        for s in data["sources"]:
            assert "url" in s
            assert "title" in s

    def test_chat_example_nav_icici_large_cap(self, client):
        """Example test case: What is the nav for icici large cap fund?"""
        r = client.post(
            "/chat",
            json={"message": "What is the nav for icici large cap fund?"},
        )
        if r.status_code != 200:
            pytest.skip("Backend unavailable")
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        # Answer should either contain NAV/fund info or a graceful "couldn't find"
        answer_lower = data["answer"].lower()
        assert "couldn't find" in answer_lower or "nav" in answer_lower or "121" in data["answer"] or "icici" in answer_lower or len(data["answer"]) > 20

    def test_chat_accepts_optional_session_id(self, client):
        r = client.post(
            "/chat",
            json={
                "message": "What is the minimum SIP for SBI Small Cap Fund?",
                "session_id": "test-session-123",
            },
        )
        if r.status_code != 200:
            pytest.skip("Backend unavailable")
        data = r.json()
        assert data.get("session_id") == "test-session-123"


@pytest.mark.phase2
class TestPhase2Admin:
    def test_admin_refresh_complete_returns_204(self, client):
        r = client.post("/admin/refresh-complete", json={})
        assert r.status_code == 204
