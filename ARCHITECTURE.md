# IndMoney RAG Chatbot – Phase-wise Architecture

## Overview

This document defines the detailed phase-wise architecture for a **RAG (Retrieval-Augmented Generation) chatbot** that answers user questions using data from **https://www.indmoney.com/**, with **Phase 1** scoped to **SBI mutual fund pages** and related content. Later phases cover the **chat application (backend & frontend)**, a **scheduler** to keep data fresh and trigger pipelines, multi-AMC expansion, UX/scale, and personalisation/compliance.

### Repository structure

- **`phase1/`** – Phase 1 code (crawl, parse, chunk, embed, RAG, query). Uses `data/scraped_funds.json` and `chroma_db/` at project root.
- **`phase2/`** – Chat app (backend & frontend) – placeholder.
- **`phase3/`** – Scheduler – placeholder.
- **`phase4/`** – Multi-AMC & fresh data: extended fund URLs, blog/help/comparison pages, same Chroma; evaluation.
- **`phase5/`** – UX & scale: last_updated (courses.json), /meta, cache, rate limiting.
- **`phase6/`** – Personalisation & compliance – placeholder.

Chunks (vector store) can be built from the updated **`data/scraped_funds.json`** by running Phase 1 with `--from-json`, so answers and their **source URLs** stay in sync with the scraped data.

### Phase Summary

| Phase | Name | Purpose |
|-------|------|--------|
| **1** | SBI Mutual Fund Data & Core RAG | Crawl, parse, chunk, embed, and store IndMoney SBI MF data; RAG retrieval + LLM generation. |
| **2** | Chat Application – Backend & Frontend | Backend API (`/chat`) and frontend chat UI; users get answers with citations. |
| **3** | Data Refresh Scheduler | Run Phase 1 pipeline on a schedule; update vector store; trigger downstream so chat and other phases always use latest data. |
| **4** | Multi-AMC & Fresh Data (planned) | Extend to all AMCs; more pages; evaluation. |
| **5** | UX & Scale (planned) | Multi-turn chat, better UI, caching, monitoring. |
| **6** | Personalisation & Compliance (planned) | User context, disclaimers, audit, feedback. |

### Chatbot behaviour and guardrails

These rules apply to all phases where the chatbot answers user questions:

1. **Answer only from stored information (embeddings)**  
   The chatbot must **not** answer from its own knowledge or general training. It must use **only** information that comes from the **retrieved chunks** (vector store / embeddings). If the retrieved context does not contain enough to answer the question, the chatbot must say so (e.g. “I couldn’t find that in the available information”) and must not invent or infer an answer.

2. **No personal information**  
   Any question that asks for, or is about, **personal information** (e.g. user identity, contact details, financial position, account details, or any other private data) is **out of scope**. The chatbot must **not** answer such questions and must respond clearly that it does not handle personal information and is only for factual mutual fund information from the indexed content.

---

## Phase 1: SBI Mutual Fund Data & Core RAG (Current Scope)

### 1.1 Objectives

- Ingest and index **mutual fund–related content** from indmoney.com.
- **Primary focus:** SBI Mutual Fund scheme pages and supporting pages (blog, collections, AMC).
- Support user questions on:
  - **Expense ratio**
  - **ELSS lock-in** (3 years, tax benefits)
  - **Minimum SIP / minimum lumpsum**
  - **Exit load**
  - **Riskometer / benchmark**
  - **How to download capital-gains statement** (IndMoney app flow)
  - Any other factual content present on the crawled mutual fund pages.

### 1.2 Data Sources (Phase 1)

| Source Type | URL Pattern / Examples | Content Relevance |
|-------------|------------------------|-------------------|
| **SBI AMC landing** | `https://www.indmoney.com/mutual-funds/amc/sbi-mutual-fund` | List of SBI schemes; AMC-level context |
| **Individual SBI fund pages** | `https://www.indmoney.com/mutual-funds/<fund-slug>-<id>` e.g. `sbi-contra-fund-direct-growth-2612`, `sbi-small-cap-fund-direct-plan-growth-3603`, `sbi-elss-tax-saver-fund-direct-growth-2754` | **Expense ratio**, **Min Lumpsum/SIP**, **Exit load**, **Benchmark**, **Lock-in**, **Riskometer**, NAV, returns, AUM, FAQs |
| **ELSS collection** | `https://www.indmoney.com/mutual-funds/collection/elss-funds` | ELSS definition, **3-year lock-in**, tax 80C, list including SBI ELSS |
| **Mutual funds hub** | `https://www.indmoney.com/mutual-funds` | General MF concepts, links to SBI funds, FAQs (taxation, exit load, expense ratio) |
| **Blog / help (supporting)** | e.g. `.../blog/mutual-funds/exit-load-mutual-funds-explained`, `.../blog/mutual-funds/what-is-expense-ratio`, `.../blog/mutual-funds/taxation-on-mutual-funds-indmoney` | Deeper explanations for **exit load**, **expense ratio**, **capital gains**, **capital-gains statement** context |
| **Capital gains / tax reports** | IndMoney app flow: More → Taxation & Report → Mutual Fund → FY → Download | Document as **procedural content** (how to download capital-gains statement) from help/blog if available, or from curated FAQ |

**Data points to extract per SBI fund page (where present):**

- Fund name, AMC (SBI Mutual Fund), category (e.g. Equity – Contra, ELSS).
- **Expense ratio** (e.g. 0.71%).
- **Benchmark** (e.g. BSE 100 India TR INR).
- **Exit load** (e.g. 0.2%; 0.25% for 0–30 days, 0.1% for 30–90 days).
- **Min Lumpsum / Min SIP** (e.g. ₹5,000 / ₹500).
- **Lock-in** (No Lock-in, or 3 years for ELSS).
- **Riskometer** (e.g. “Very High Risk”).
- AUM, inception date, fund manager(s).
- Short “About” and key FAQs (NAV, returns, exit load, expense ratio, top holdings).

### 1.3 Phase 1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: DATA & RAG PIPELINE                          │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
  │  1. CRAWL /      │     │  2. PARSE &      │     │  3. CHUNK &      │
  │     FETCH        │────▶│     CLEAN         │────▶│     ENRICH       │
  └──────────────────┘     └──────────────────┘     └──────────────────┘
         │                           │                         │
         ▼                           ▼                         ▼
  • IndMoney URLs             • HTML → text/          • Semantic chunks
    (SBI AMC, fund pages,       structure              (by section:
    ELSS collection,            (tables, FAQs,          overview, metrics,
    /mutual-funds,              overview)               exit load, FAQ)
    blog articles)             • Dedupe, normalise    • Metadata: fund_name,
  • Respect robots.txt          units (%, ₹)           source_url, type
  • Rate limiting             • Extract key fields     (fund_page, blog,
  • Optional: sitemap            into structured        collection)
                                metadata               • Optional: fund_id,
                                                         AMC, category
         │                           │                         │
         └───────────────────────────┴─────────────────────────┘
                                         │
                                         ▼
  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
  │  4. EMBED &       │     │  5. RETRIEVAL    │     │  6. GENERATION   │
  │     STORE         │────▶│     (RAG)        │────▶│     (LLM)        │
  └──────────────────┘     └──────────────────┘     └──────────────────┘
         │                           │                         │
         ▼                           ▼                         ▼
  • Embedding model             • User query →           • Prompt: system
    (e.g. sentence-               vector search             (IndMoney/SBI
    transformers,                 + optional                context) +
    OpenAI/other)                 keyword filter            retrieved chunks
  • Vector DB                    • Top-k chunks             + user question
    (Chroma,                      • Optional: filter        • Output: answer
    Pinecone,                     by source_type,           + citations
    pgvector, etc.)                 fund_name                (source URLs)
  • Metadata stored              • Re-ranking                 and “I don’t
    for filtering                   (optional)                 know” when
                                                                 no match
```

### 1.4 Component Specifications (Phase 1)

#### 1.4.1 Crawl / Fetch

- **Input:** Seed URLs (SBI AMC, known SBI fund URLs, ELSS collection, mutual-funds hub, selected blog URLs).
- **Mechanism:** 
  - Web scraper/crawler (e.g. Scrapy, Playwright, or requests + BeautifulSoup) with polite crawling (rate limit, User-Agent).
  - Discover SBI fund links from AMC page and from `/mutual-funds/all` or category pages filtered by “SBI”.
- **Output:** Raw HTML (or pre-rendered HTML if site is JS-heavy).
- **Compliance:** Respect `robots.txt`; consider caching and incremental updates.

#### 1.4.2 Parse & Clean

- **Input:** Raw HTML.
- **Actions:**
  - Strip navigation, ads, footers; keep main content and FAQs.
  - Convert tables to structured text (e.g. “Expense ratio: 0.71%”, “Exit load: 0.2%”).
  - Normalise numbers (%, ₹, Cr) for consistency.
  - Extract structured fields (expense_ratio, min_sip, exit_load, benchmark, lock_in, riskometer) per fund page for metadata/store.
- **Output:** Clean text per page + optional JSON per fund (for metadata filtering).

#### 1.4.3 Chunk & Enrich

- **Chunking:** Semantic chunks (e.g. 300–600 tokens with overlap) by section (Overview, Performance, Exit load, FAQ, etc.).
- **Metadata per chunk:** `source_url`, `fund_name`, `amc` (e.g. SBI Mutual Fund), `page_type` (fund_page | blog | collection | amc), and key fields if available (expense_ratio, exit_load, etc.).
- **Enrichment:** Add short context line where helpful (e.g. “SBI Contra Fund: Expense ratio 0.71%”) for better retrieval.

#### 1.4.4 Embed & Store

- **Embedding:** Use a single embedding model for all chunks (e.g. `sentence-transformers` or provider API).
- **Vector store:** Store vector + metadata; support filter by `page_type`, `fund_name`, `amc`.
- **Indexing:** Run after each crawl/refresh; version or timestamp for reproducibility.

#### 1.4.5 Retrieval (RAG)

- **Query:** User question (e.g. “What is the expense ratio of SBI Contra Fund?” or “How to download capital gains statement?”).
- **Steps:**
  1. Optional query expansion (e.g. “capital gains statement” → “download capital gains report mutual fund IndMoney”).
  2. Vector search with top-k (e.g. k=5–10).
  3. Optional filter: e.g. only `fund_page` + `amc = SBI` for fund-specific questions.
  4. Optional re-ranker for better ordering.
- **Output:** Ordered list of chunks with `source_url` and snippet for citations.

#### 1.4.6 Generation (LLM)

- **Prompt structure:**
  - **System:** You are a helpful assistant for IndMoney mutual fund information. Answer **only** from the provided context. Do not use your own knowledge. If the context does not contain the answer, say so. Cite sources (URLs) where relevant. Do not answer questions about personal information; say that is out of scope.
  - **User:** Context: [retrieved chunks]. Question: [user question].
- **Output:** Natural language answer + source links (e.g. “Source: https://www.indmoney.com/mutual-funds/sbi-contra-fund-direct-growth-2612”).
- **Guardrails:** Answer only from retrieved context (see **Chatbot behaviour and guardrails**). No advice on “should you invest”; stick to factual content from IndMoney. No personal information.

### 1.5 Phase 1 Data Flow (Summary)

1. **Crawl** indmoney.com for SBI AMC, all SBI fund pages, ELSS collection, mutual-funds hub, and selected blog/help pages.
2. **Parse** to text + structured fields (expense ratio, exit load, min SIP, benchmark, riskometer, lock-in).
3. **Chunk** with metadata (fund name, URL, page type).
4. **Embed** and store in vector DB.
5. **On user query:** retrieve relevant chunks → LLM generates answer with citations.

### 1.6 Example User Questions (Phase 1)

- “What is the expense ratio of SBI Contra Fund?”
- “What is the minimum SIP for SBI Small Cap Fund?”
- “Does SBI ELSS Tax Saver have a lock-in? How many years?”
- “What is the exit load for SBI Contra Fund?”
- “What is the riskometer and benchmark for SBI Contra Fund?”
- “How do I download my capital gains statement for mutual funds on IndMoney?”
- “Which SBI funds have no lock-in?”

### 1.7 Technology Suggestions (Phase 1)

| Layer | Options |
|-------|--------|
| Crawl/Fetch | Python + requests/httpx, BeautifulSoup, Playwright (if JS rendering needed) |
| Parse/Clean | BeautifulSoup, lxml, custom extractors for tables/FAQs |
| Chunking | LangChain TextSplitter, LlamaIndex, or custom (sentence/paragraph + overlap) |
| Embeddings | sentence-transformers (e.g. all-MiniLM-L6-v2), OpenAI embeddings, or Cohere |
| Vector DB | Chroma, FAISS, Pinecone, pgvector, Weaviate |
| LLM | **Groq** (production for Phase 3 chat); alternatives: OpenAI GPT-4o-mini, Anthropic Claude, or local (e.g. Llama) |
| App | FastAPI/Flask + simple front-end (chat UI); optional Slack/WhatsApp later |

### 1.8 Phase 1 URL Checklist (Implementation)

Use these as seed URLs for the crawler. SBI fund list should be discovered from the AMC page and from `/mutual-funds/all` (filter by SBI).

| Purpose | URL |
|--------|-----|
| SBI AMC | `https://www.indmoney.com/mutual-funds/amc/sbi-mutual-fund` |
| ELSS collection (lock-in, tax) | `https://www.indmoney.com/mutual-funds/collection/elss-funds` |
| Mutual funds hub (FAQs) | `https://www.indmoney.com/mutual-funds` |
| All funds (discover SBI) | `https://www.indmoney.com/mutual-funds/all` |
| Example SBI fund pages | `sbi-contra-fund-direct-growth-2612`, `sbi-small-cap-fund-direct-plan-growth-3603`, `sbi-elss-tax-saver-fund-direct-growth-2754` |
| Blog – exit load | `https://www.indmoney.com/blog/mutual-funds/exit-load-mutual-funds-explained` |
| Blog – expense ratio | `https://www.indmoney.com/blog/mutual-funds/what-is-expense-ratio` |
| Blog – taxation/capital gains | `https://www.indmoney.com/blog/mutual-funds/taxation-on-mutual-funds-indmoney` |

**Capital gains statement (procedural):** Document in knowledge base: “In IndMoney app: More → Taxation & Report → Mutual Fund → Select financial year → Download” (and add help/blog URL if IndMoney publishes one).

### 1.9 Out of Scope for Phase 1

- Non-SBI AMC funds (Phase 4).
- Real-time NAV/price feeds (Phase 4+).
- User accounts, portfolios, or personalised advice (later phases).
- Legal/regulatory disclaimer handling (can be added as static text in Phase 2).

---

## Phase 2: Chat Application – Backend & Frontend

### 2.1 Objectives

- Expose the Phase 1 RAG pipeline as a **chat service** with a clear API.
- Provide a **frontend** chat UI so users can ask questions and receive answers with citations.
- Keep backend and frontend modular so the scheduler (Phase 3) and other phases can integrate without changing the chat contract.

### 2.2 Backend

- **Responsibilities:**
  - Accept user messages (single-turn in MVP; multi-turn in Phase 5).
  - Call the RAG pipeline: retrieve chunks from the vector store, then generate a response via the LLM.
  - Return the answer plus source URLs (and optional chunk snippets) for citations.
  - Optional: conversation/session ID for future multi-turn.
- **API shape (example):**
  - `POST /chat` – body: `{ "message": "What is the expense ratio of SBI Contra Fund?" }` → response: `{ "answer": "...", "sources": [{ "url": "...", "title": "..." }] }`.
  - `GET /health` – readiness for load balancer/scheduler.
- **Tech:** FastAPI or Flask; async where useful (e.g. non-blocking LLM calls).
- **Config:** Vector store connection, embedding model, LLM endpoint and keys (via env/config).
- **Error handling:** Timeouts, LLM failures, empty retrieval → graceful “I couldn’t find…” or “Please try again.”

### 2.3 Frontend

- **Responsibilities:**
  - Chat interface: input box, send button, message list (user + assistant).
  - Render assistant messages with **citations** (e.g. “Source: …” links).
  - Loading state while the backend is processing.
  - Optional: disclaimer text (e.g. “For informational purposes only”) in footer or first message.
- **Tech:** React, Next.js, or Vue; or a simple static HTML/JS page calling the backend.
- **Deployment:** Can be served by the same app (e.g. FastAPI static files) or a separate frontend host; CORS configured for the backend domain.

### 2.4 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: CHAT APPLICATION                                  │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
  │   Frontend   │  HTTP   │   Backend    │  uses   │  Phase 1     │
  │   (Chat UI)  │────────▶│   /chat API  │────────▶│  RAG pipeline│
  └──────────────┘         └──────────────┘         └──────────────┘
         ▲                         │                         │
         │                         │                         ▼
         │                  answer + sources           Vector DB
         └─────────────────────────┘                   + LLM
```

### 2.5 Out of Scope for Phase 2

- User login and persistence of chat history (Phase 6).
- Multi-turn conversation memory (Phase 5).
- Scheduling and data refresh (Phase 3).

---

## Phase 3: Data Refresh Scheduler

### 3.1 Objectives

- Run the **Phase 1 data pipeline** on a schedule so the vector store and RAG always use **up-to-date** content from indmoney.com.
- After refreshing data, **trigger or notify** any dependent components (e.g. re-index ready, cache invalidation) so the chat application and other phases see the latest data every time.

### 3.2 LLM: Groq

- The chatbot uses **Groq** as the LLM for answer generation (e.g. in the Phase 2 chat backend or when an LLM is integrated).
- Groq is used **only** to turn the **retrieved chunks** (from the embeddings/vector store) into a natural-language answer. The model must **not** answer from its own knowledge; it must use **only** the provided context (see **Chatbot behaviour and guardrails**).
- Configuration: Groq API key and model (e.g. via env); all generation requests pass the retrieved context and user question to Groq and return the response plus source URLs.

### 3.3 Scheduler Role

1. **Trigger Phase 1 pipeline** at configured intervals (e.g. daily or weekly):
   - Crawl → Parse → Chunk → Embed → Store (full or incremental).
2. **On success:** Optionally trigger downstream steps (e.g. “index ready” event, webhook, or internal API call) so that:
   - Backend/chat uses the new index (e.g. switch alias or reload).
   - Any caches (e.g. response cache) can be invalidated if needed.
3. **On failure:** Alert (e.g. log, email, or Slack) and optionally retry; do not replace the existing index until a successful run.

### 3.4 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3: DATA REFRESH SCHEDULER                            │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────┐
  │  Scheduler       │  (cron / Celery / Airflow / Kubernetes CronJob)
  │  (time-based)    │
  └────────┬─────────┘
           │
           │ 1. Trigger at schedule (e.g. daily 2 AM)
           ▼
  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
  │  Phase 1:        │     │  Phase 1:        │     │  Phase 1:        │
  │  Crawl / Fetch   │────▶│  Parse → Chunk   │────▶│  Embed & Store   │
  └──────────────────┘     └──────────────────┘     └────────┬─────────┘
                                                                 │
           │ 2. On success: trigger downstream                   │
           ▼                                                     ▼
  ┌──────────────────┐                              ┌──────────────────┐
  │  Notify / Trigger │                              │  Vector DB       │
  │  downstream       │                              │  (updated index) │
  └────────┬─────────┘                              └──────────────────┘
           │
           ├──▶ Invalidate caches (if any)
           ├──▶ Switch index alias or reload (if applicable)
           └──▶ Phase 2 chat backend uses updated data on next request
```

### 3.5 Implementation Options

| Option | Use case |
|--------|----------|
| **Cron** | Simple: one script that runs Phase 1 pipeline then exits; cron triggers at fixed time. |
| **Celery Beat** | If app is already Python/Celery: periodic task that runs the pipeline and can enqueue “post-refresh” tasks. |
| **Airflow / Prefect** | DAG: Crawl → Parse → Chunk → Embed → Store → “Notify” task; full audit and retries. |
| **Kubernetes CronJob** | Container that runs the pipeline on schedule; good when everything is in K8s. |

### 3.6 Downstream “Trigger” Behaviour

- **Vector store:** Phase 1 pipeline writes to the same store (e.g. replace collection or upsert by URL). Chat backend already reads from that store; no code change needed if the backend always queries the default/current index.
- **Optional explicit steps after refresh:**
  - Call backend `POST /admin/refresh-complete` to clear in-memory caches.
  - Or use a “index version” / “last_updated” that the backend checks to decide cache TTL.
- **Other phases:** When Phase 4+ (multi-AMC, analytics, etc.) exist, the same scheduler can run their ingestion or re-index jobs after Phase 1 (e.g. “Phase 1 → Phase 4 full re-crawl” once a week).

### 3.7 Configuration

- **Schedule:** e.g. `0 2 * * *` (daily 2 AM); or weekly Sunday 3 AM.
- **Timeout and retries:** Pipeline should have a max duration and retry policy so the scheduler does not hang.
- **Idempotency:** Re-running the pipeline should produce a consistent state (e.g. full replace or upsert by document ID).

### 3.8 Out of Scope for Phase 3

- Real-time streaming of site changes (only scheduled refresh).
- User-facing “last updated” in the UI (can be added in Phase 5).

---

## Phase 4 (Planned): Multi-AMC & Fresh Data

- Extend crawl to **all AMCs** (or configurable list) on indmoney.com.
- **Scheduling:** Already covered by Phase 3; this phase extends *what* is crawled, not how often.
- **Enhancements:** More blog/help pages, comparison pages, calculator pages (for “how returns are calculated” type Q&A).
- **Evaluation:** Accuracy and citation quality on held-out questions.

---

## Phase 5 (Planned): UX & Scale

- **Conversation:** Multi-turn chat, follow-up questions.
- **UI:** Better citations, “Related funds” or “Related articles.”
- **Scale:** Caching, rate limiting, monitoring.
- **Optional:** Voice input, multi-language.
- **Optional:** Show “Data last updated: …” using Phase 3 metadata.

---

## Phase 6 (Planned): Personalisation & Compliance

- **User context:** Logged-in user’s holdings (if permitted by product).
- **Compliance:** Disclaimers, audit log of answers, no guarantee of returns.
- **Feedback loop:** Thumbs up/down, “Report error” to improve retrieval/prompts.

---

## Document Control

- **Version:** 1.1  
- **Phase 1:** SBI mutual fund data & RAG pipeline.  
- **Phase 2:** Chat application (backend API + frontend UI).  
- **Phase 3:** Scheduler to refresh Phase 1 data and trigger downstream so the system has the latest data every time.  
- **Phases 4–6:** Multi-AMC, UX/scale, personalisation/compliance.
