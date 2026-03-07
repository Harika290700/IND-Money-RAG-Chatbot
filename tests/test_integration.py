"""
Integration tests: cross-phase flows.
- Example user query "What is the nav for icici large cap fund?" through Phase 2 API.
- Phase 1 RAG + Phase 2 chat contract (answer + sources).
"""
import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.mark.integration
class TestIntegrationChatWithRAG:
    """Run example query through Phase 2; backend uses Phase 1 RAG (+ optional Groq)."""

    def test_nav_icici_large_cap_via_phase2(self):
        from fastapi.testclient import TestClient
        from phase2.app import app
        client = TestClient(app)
        r = client.post(
            "/chat",
            json={"message": "What is the nav for icici large cap fund?"},
        )
        assert r.status_code in (200, 500)  # 500 if Chroma/LLM not available
        if r.status_code != 200:
            pytest.skip("Chroma or LLM not available for integration")
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        # Expect either a substantive answer (NAV/fund) or graceful fallback
        assert len(data["answer"]) > 10
        if data["sources"]:
            assert all("url" in s and "title" in s for s in data["sources"])

    def test_expense_ratio_sbi_contra_via_phase2(self):
        from fastapi.testclient import TestClient
        from phase2.app import app
        client = TestClient(app)
        r = client.post(
            "/chat",
            json={"message": "What is the expense ratio of SBI Contra Fund?"},
        )
        if r.status_code != 200:
            pytest.skip("Backend unavailable")
        data = r.json()
        assert "answer" in data and "sources" in data
        assert len(data["answer"]) > 10

    def test_personal_info_out_of_scope(self):
        from fastapi.testclient import TestClient
        from phase2.app import app
        client = TestClient(app)
        r = client.post(
            "/chat",
            json={"message": "What is my account balance?"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "personal" in data["answer"].lower() or "out of scope" in data["answer"].lower() or "don't handle" in data["answer"].lower()
        assert data["sources"] == []
