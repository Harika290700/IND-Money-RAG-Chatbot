# Tests

Test cases for Phase 1 (RAG/LLM), Phase 2 (Chat API), Phase 3 (scheduler), and integration.

## Setup

From **project root**:

```bash
pip install -r requirements.txt
```

## Run all tests

```bash
# From project root
pytest tests/ -v
```

## Run only unit tests (skip integration)

Integration tests require the Phase 1 vector store (Chroma) to be built. Skip them if you haven’t run the pipeline yet:

```bash
pytest tests/ -v -m "not integration"
```

## Run only integration tests

Requires `chroma_db/` to exist (run `python -m phase1.run_pipeline --from-json` first):

```bash
pytest tests/ -v -m "integration"
```

## Example test case

The user query **"What is the nav for icici large cap fund?"** is covered by:

- **Phase 1:** `tests/test_phase1_rag.py::TestPhase1RetrieveIntegration::test_example_nav_query_icici_large_cap`
- **Phase 2:** `tests/test_phase2_api.py::TestPhase2Chat::test_chat_example_nav_icici_large_cap`
- **Integration:** `tests/test_integration.py::TestIntegrationChatWithRAG::test_nav_icici_large_cap_via_phase2`

Run them with:

```bash
pytest tests/test_phase1_rag.py -v -m integration -k "nav"
pytest tests/test_phase2_api.py -v -k "nav"
pytest tests/test_integration.py -v -k "nav"
```

## Markers

- `integration` – needs Chroma / vector store (and optionally Groq for full flow).
- `phase2` – Phase 2 API tests.
- `phase3` – Phase 3 scheduler tests.
