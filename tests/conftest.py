"""
Pytest configuration and shared fixtures.
Tests are run from project root: pytest tests/
"""

import sys
from pathlib import Path

# Project root on path so imports like phase1.rag, phase2.app work
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks tests that need Chroma/vector store (deselect with -m 'not integration')")
    config.addinivalue_line("markers", "phase2: marks Phase 2 API tests")
    config.addinivalue_line("markers", "phase3: marks Phase 3 scheduler tests")
