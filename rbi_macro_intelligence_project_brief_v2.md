# Policy Intelligence — Practical Project Brief

## 1. Project in one sentence

Build a low-cost personal **India Macro & RBI Intelligence System** that automatically collects trusted economic/RBI information, detects what changed, connects developments to macro/financial concepts, and produces a short daily/weekly intelligence brief — rather than functioning as a generic Q&A chatbot.

## 2. Why I am building it

Personal goals:

- Rebuild my understanding of the Indian economy, monetary policy and RBI.
- Stay updated without reading dozens of documents/news articles every day.
- Learn macro-finance concepts through repeated real-world examples.

Portfolio goals:

- Demonstrate a real AI application, not a toy chatbot.
- Demonstrate RAG, information extraction, structured LLM workflows, evaluation, APIs, data engineering and deployment.
- Keep the project small enough for one person to build in roughly 2–4 weeks with an AI coding assistant.



## 3. Core product

The application should answer:

### "What changed in India's economic/financial environment, why does it matter, and what should I understand next?"

The main output is a **Daily Macro Brief**, with sections such as:

1. **Top developments**
  - 5–8 important developments since the previous brief.
  - Each item links to its source.
2. **What changed**
  - New RBI policy/notification/speech/report.
  - Important macroeconomic data releases.
  - Relevant global developments affecting India.
3. **Why it matters**
  - Explain the likely transmission mechanism.
  - Clearly distinguish facts from interpretation.
4. **RBI watch**
  - Inflation
  - Growth
  - Liquidity
  - Banking/credit
  - INR/FX
  - Financial stability
  - Policy stance
5. **Fintech/NBFC lens**
  - Possible implications for lending, funding costs, credit growth, asset quality and NBFCs.
6. **One concept to learn**
  - Pick one relevant concept from the day's events.
  - Example: VRRR, real policy rate, yield curve, CRR, liquidity transmission, OMO, NIM, credit impulse.
7. **What to watch next**
  - Upcoming releases, MPC meetings, important events and unresolved themes.



## 4. Sources — keep the first version small



### Tier 1: authoritative sources

Start with:

- RBI press releases
- RBI MPC statements
- RBI Bulletin
- RBI speeches
- RBI notifications/circulars
- RBI statistical releases



### Tier 2: official economic data

Add later:

- MOSPI
- Ministry of Finance
- Department of Economic Affairs
- Government economic releases

#### RBI website access constraint

RBI or any official website may use anti-bot protections on some pages. The application must NOT attempt to bypass CAPTCHAs, access controls, rate limits, or other anti-bot mechanisms.

Design ingestion to use publicly accessible and permitted sources wherever possible, prioritizing:

- Direct RBI PDF/document URLs

- Public RBI publication/document endpoints

- Official RBI feeds or structured sources, if available

- Other official government sources where appropriate

If a source cannot be reliably and legitimately accessed programmatically, do not build a workaround to circumvent the restriction. Find an alternative official source or make that source manually ingestible.

The system should:

- Respect `robots.txt` where applicable

- Use conservative request rates

- Cache previously retrieved documents

- Avoid repeatedly requesting unchanged pages

- Store source URLs and publication dates

- Log ingestion failures clearly

Before implementing any scraper/collector, verify that the specific RBI source is technically accessible and appropriate for automated retrieval. Do not assume that because a document is publicly viewable in a browser, it is suitable for automated scraping.

### Tier 3: news

Add only after the core RBI pipeline works.
Use a small number of reputable sources and store the source URL and publication date.

Do NOT attempt to crawl the entire internet.

## 5. MVP scope

The first version should NOT contain:

- A fully autonomous agent swarm.
- Stock-price prediction.
- Trading recommendations.
- Hundreds of data sources.
- Complex forecasting models.
- A mobile application.
- Paid APIs unless absolutely necessary.



### MVP pipeline

```text
RBI sources
   ↓
Scheduled ingestion
   ↓
Document extraction + cleaning
   ↓
Deduplication + metadata
   ↓
SQLite/PostgreSQL
   ↓
Embeddings / retrieval
   ↓
LLM extraction + classification
   ↓
Daily brief generation
   ↓
Simple web dashboard
```



## 6. Suggested MVP features



### A. Ingestion

- Scheduled Python job.
- Fetch new RBI documents/pages.
- Store:
  - title
  - date
  - source
  - URL
  - document type
  - raw/clean text
  - hash for deduplication



### B. Classification

Classify documents into a small controlled taxonomy:

- Monetary Policy
- Liquidity
- Banking
- Regulation
- Inflation
- Growth
- FX/External Sector
- Financial Stability
- Payments
- Other



### C. Event extraction

For each important document, extract structured fields:

```json
{
  "event": "...",
  "date": "...",
  "category": "...",
  "entities": ["RBI", "..."],
  "indicators": ["repo rate", "..."],
  "direction": "increase/decrease/unchanged",
  "importance": 1,
  "summary": "...",
  "source_url": "..."
}
```



### D. Retrieval

Use embeddings/vector search to retrieve relevant source passages.

Important: generated claims must be grounded in retrieved source text.

### E. Brief generation

Generate the Daily Macro Brief from structured events + retrieved evidence.

Every factual statement should have a source citation/link.

### F. Learning layer

For each brief:

- identify one relevant macro/finance concept;
- explain it simply;
- connect it to the day's event;
- optionally provide a tiny "check yourself" question.



## 7. Evaluation — important for portfolio value

Do not simply say "the LLM works."

Create a small evaluation set (e.g. 30–50 questions/examples) and measure:

- Retrieval relevance
- Citation correctness
- Factual accuracy
- Unsupported-claim/hallucination rate
- Classification accuracy
- Brief usefulness

Manually review the first evaluation set.

## 8. Tech stack — keep it boring

Recommended initial stack:

- Python
- FastAPI
- SQLite initially
- PostgreSQL only if deployment needs it
- pgvector or a lightweight vector store
- Pydantic
- OpenAI/Anthropic API
- Simple Streamlit frontend OR lightweight React frontend
- Docker
- GitHub
- One inexpensive cloud deployment

Do not over-engineer the stack.

## 9. Architecture principles

- Separate ingestion from analysis.
- Store source documents before sending them to an LLM.
- Prefer structured outputs over free-form LLM responses.
- Make every AI-generated claim traceable to source evidence.
- Make ingestion idempotent.
- Keep LLM calls replaceable.
- Keep prompts/versioning in the repository.
- Add tests around parsing, deduplication and retrieval.
- Never let an LLM silently invent economic data.



## 10. Dashboard

Keep the UI simple.

### Home

- Today's macro regime snapshot
- Latest Daily Brief
- Key indicators
- "What changed?"



### Explore

Filter by:

- date
- category
- source
- topic



### Learn

- Concepts encountered
- Short explanations
- Historical examples

Do not spend weeks making the UI pretty.

## 11. Deployment target

The final MVP should be accessible through a public URL.

Minimum production setup:

```text
Docker
  ↓
FastAPI
  ↓
Database
  ↓
Scheduled ingestion job
  ↓
LLM API
```

Include:

- environment variables/secrets
- logging
- health endpoint
- basic error handling
- GitHub README
- architecture diagram
- deployment instructions



## 12. Portfolio story

The project should be presented as:

> **RBI Macro Intelligence — an AI-powered macroeconomic intelligence system that turns fragmented RBI and economic information into a source-grounded daily intelligence brief.**

The interesting engineering problem is NOT summarization.

It is:

- finding relevant information,
- deciding what matters,
- extracting structured economic events,
- retrieving evidence,
- connecting events to concepts,
- generating grounded analysis,
- evaluating factuality and retrieval quality,
- and deploying the whole pipeline.



## 13. Build order



### Phase 1 — 1–2 days

- Repository
- Architecture
- RBI ingestion
- Database
- Store documents



### Phase 2 — 2–3 days

- Cleaning
- Deduplication
- Classification
- Event extraction



### Phase 3 — 2–3 days

- Embeddings
- Retrieval
- Source-grounded generation



### Phase 4 — 2–3 days

- Daily Brief
- Learning layer
- Dashboard



### Phase 5 — 2–3 days

- Evaluation
- Tests
- Docker
- Deployment
- README/demo

Target: a functional MVP in ~2 weeks of focused work, with optional improvements afterward.

## 14. Later extensions — only if the MVP is finished

Potential V2:

- Macro indicator time series
- "What changed from last month?"
- Historical event retrieval
- Topic timelines
- RBI policy stance tracker
- Simple macro relationships/visualizations
- Email/Telegram daily brief
- News triangulation
- Contradiction detection between sources
- Personal learning progress

Do NOT start V2 before MVP deployment.

## 15. Questions the coding LLM should ask before implementing

Before making major architectural decisions, clarify:

1. Which sources are in scope for the current milestone?
2. What is the smallest useful implementation?
3. What data needs to be persisted?
4. Where does each generated claim get its evidence?
5. How will this component be tested?
6. Is this complexity actually necessary for the MVP?



## 16. Coding-agent instructions

Act as a senior AI/ML engineer helping an individual build this project.

Rules:

- Work incrementally.
- Do not generate the entire application in one response.
- Explain the purpose of each major component briefly.
- Prefer simple production-quality solutions.
- Write tests for important logic.
- Never invent APIs or undocumented library behavior.
- Before changing architecture, explain the trade-off.
- Keep the project deployable at every milestone.
- Use Git commits/milestones.
- When debugging, inspect the actual error before proposing a fix.
- Do not add technologies just because they are fashionable.



## 17. Definition of done

The project is considered complete when:

- New RBI documents can be ingested automatically.
- Documents are persisted and deduplicated.
- Important documents/events are classified and structured.
- Retrieval returns relevant evidence.
- Daily Brief is generated from retrieved evidence.
- Claims have source links.
- Basic evaluation exists.
- Application is Dockerized.
- Application is deployed.
- README explains architecture and trade-offs.
- I can demo it in 5 minutes.
- I can explain why each AI component exists.



## 18. Important product constraint

This is a **personal financial education/intelligence tool**, not a financial-advice or trading system.

Do not make investment recommendations or present speculative interpretations as facts.

---



# Current development philosophy

Build the smallest useful version first.

The goal is NOT:

> "Build an autonomous financial AI agent."

The goal is:

> "Build something I genuinely use every morning to understand what is happening in India, while demonstrating that I can build and deploy a grounded AI application end-to-end."



## 19. Cost, scalability and deployment trade-off analysis

Before deployment, explicitly evaluate the system as a real application rather than assuming the first architecture is production-ready.

Compare:

- LLM API cost per document and per generated brief
- Embedding cost
- Database/vector-store cost
- Hosting/compute cost
- Estimated monthly cost for personal use
- Estimated cost at 10 / 100 / 1,000 users
- Latency of the main workflow
- Batch vs real-time processing
- Caching opportunities
- Rate limits and API constraints
- Likely scaling bottlenecks

For important components, compare reasonable alternatives where useful:

- Hosted LLM API vs smaller/local model
- Managed vector DB vs PostgreSQL/pgvector
- Scheduled batch processing vs on-demand processing
- Cheap single-instance deployment vs more scalable architecture

The goal is NOT to optimize prematurely. The goal is to:

1. Measure/estimate the MVP's cost and latency.
2. Understand the trade-offs behind the chosen architecture.
3. Document what would change if usage increased significantly.
4. Be able to defend the architecture in an AI/ML engineering interview.

Include a short **Cost & Scalability** section in the final README with assumptions, approximate calculations, chosen architecture, alternatives considered, and the conditions under which the architecture should change.