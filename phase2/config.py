"""
Phase 2: Backend configuration from environment.
Vector store and embedding model come from Phase 1 (chroma_db, sentence-transformers).
LLM (Groq) and server settings below.
"""

import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Server
PHASE2_HOST = os.environ.get("PHASE2_HOST", "0.0.0.0")
PHASE2_PORT = int(os.environ.get("PHASE2_PORT", "8000"))

# Groq LLM (used only to generate answer from retrieved chunks)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant").strip()
LLM_TIMEOUT_SEC = int(os.environ.get("PHASE2_LLM_TIMEOUT_SEC", "1"))
if LLM_TIMEOUT_SEC < 1:
    LLM_TIMEOUT_SEC = 1

# RAG: top-k retrieval (default 3 for faster LLM; override with PHASE2_TOP_K)
PHASE2_TOP_K = int(os.environ.get("PHASE2_TOP_K", "3"))
if PHASE2_TOP_K < 1:
    PHASE2_TOP_K = 3

# Optional: include a short snippet per source in response (max chars)
SOURCE_SNIPPET_MAX_CHARS = int(os.environ.get("PHASE2_SOURCE_SNIPPET_MAX_CHARS", "200"))
if SOURCE_SNIPPET_MAX_CHARS < 0:
    SOURCE_SNIPPET_MAX_CHARS = 0
