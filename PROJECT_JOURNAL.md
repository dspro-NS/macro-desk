# Macro Desk — Project Journal

Living engineering journal for Macro Desk. Entries below are reconstructed from the repository, git history, `README.md`, `rbi_macro_intelligence_project_brief_v2.md`, source code, and tests. Items that cannot be confirmed from those artifacts are marked **To verify**.

Last reconstructed from git tip: `758f77b` (`feat: add on-demand source-grounded RBI item explanations`, 2026-09-14).

---

## 1. Project Goal

Macro Desk is a personal **India macro and RBI intelligence** system. The project brief (`rbi_macro_intelligence_project_brief_v2.md`) frames the product around answering:

> What changed in India's economic/financial environment, why does it matter, and what should I understand next?

The intended long-term output is a **Daily Macro Brief** that is source-grounded rather than a generic Q&A chatbot.

What the codebase implements today is narrower than that full vision:

- Collect trusted RBI information via official RSS feeds
- Store documents idempotently in SQLite
- Classify and rank items with keyword rules (not an LLM)
- Surface “what is new to this database” via a first-seen time window
- Provide on-demand, source-grounded LLM explanations for a single stored item

The README still describes early Milestone 1 language (“stores official RBI press releases”) even though notifications, speeches, importance ranking, and explanations are present. Treat the brief as the product north star and the git history as the implemented path.

---

## 2. Architecture Evolution

Chronology from `git log` (oldest → newest):

| Date (commit) | Change |
| --- | --- |
| 2026-09-06 (`29954b4`) | Repo init: brief + `.gitignore` |
| 2026-09-07 (`9a0b61a`) | Python package: FastAPI, SQLite, RSS ingest for press releases, CLI, tests |
| 2026-09-07 (`b5e03b5`) | Rule-based taxonomy classification + DB columns + filter API |
| 2026-09-07 (`ab5e2d2`) | Notifications RSS; shared `FeedSpec` / `configured_feeds` |
| 2026-09-07 (`b96eae5`) | `ingest_runs` + `GET /changes` on `created_at` (first-seen) |
| 2026-09-07 (`c7e5171`) | Read-only HTML homepage at `GET /` |
| 2026-09-07 (`5033a67`) | Speeches RSS as third feed |
| 2026-09-07 (`7ab1e13`) | Rule-based importance (`high` / `medium` / `low`) + homepage ordering |
| 2026-09-14 (`758f77b`) | On-demand explanations: `ai/` package, OpenAI provider, cache table, UI |

### Current package layout

```text
src/macro_desk/
  api/           FastAPI app, routes, server-rendered home HTML/JS
  ai/            Explanation contracts, service, OpenAI provider
  db/            SQLite connect / initialize / DocumentRepository
  domain/        models, hashing, HTML→text, taxonomy, classification, importance
  ingestion/     FeedClient, RSS parse, FeedSpec, ingest pipeline
  cli.py         `ingest` command
  config.py      pydantic-settings (`MACRO_DESK_` prefix)
  main.py        ASGI entrypoint
tests/           pytest; ingest uses injected RSS bytes (no network)
```

### Key runtime components

- **Ingestion:** one HTTP GET per configured feed → parse RSS → classify/rank → insert or skip
- **Storage:** SQLite file (default `data/macro_desk.sqlite`); tables `documents`, `ingest_runs`, `document_explanations`
- **API:** FastAPI endpoints for health, documents, ingest, changes, explanations, and HTML home
- **AI:** optional; only wired when `MACRO_DESK_OPENAI_API_KEY` is set

---

## 3. Technical Decisions

### SQLite first

Documented in `README.md`: single-user tool, zero extra services, one-file backup, unique indexes on `source_url` and `content_hash` for idempotent inserts. PostgreSQL / vector store deferred until deployment or embeddings. Repository is a thin SQLite wrapper around domain models.

### Official RSS only; no HTML scrape / no anti-bot bypass

The brief forbids bypassing CAPTCHAs, access controls, or anti-bot mechanisms. Implementation:

- Feeds: `https://rbi.org.in/pressreleases_rss.xml`, `notifications_rss.xml`, `speeches_rss.xml`
- `FeedClient` uses a single GET with timeout + identifiable `User-Agent`
- Non-retryable statuses include `401`, `403`, `404`, `418`, `429` (`ingestion/client.py`)
- Item body = RSS `description` → `raw_text` / `clean_text` (excerpt, not full linked page)

### Shared feed pipeline via `FeedSpec`

After notifications (and later speeches), ingestion was generalized:

- `configured_feeds(settings)` returns ordered `FeedSpec(url, source_name, document_type)`
- Same parse/persist path for all three; distinct `source` / `document_type` labels
- Dedup remains **global** across feeds (`UNIQUE(source_url)`, `UNIQUE(content_hash)`)

### Rule-based classification before LLM

Commit rationale: persist a controlled taxonomy category and reason so documents can be filtered **without introducing an LLM**. Taxonomy mirrors the brief (`domain/taxonomy.py`): Monetary Policy, Liquidity, Banking, Regulation, Inflation, Growth, FX/External Sector, Financial Stability, Payments, Other. Keyword scoring with explicit tie-break order; injectable classifier protocol for later replacement.

### First-seen (`created_at`) ≠ RBI publish date (`published_at`)

Commit `b96eae5` states “what changed” is based on **first insert**, not RBI publish date. Homepage and `GET /changes` filter on `created_at >= since`. This answers “new to this desk,” not “published by RBI in the last N hours.”

### Importance ranking without hiding routine items

Commit `7ab1e13`: transparent `high` / `medium` / `low` + reason. Homepage orders high → medium → low, then newest; lows still appear. Filterable via `GET /documents?importance=…`.

### Server-rendered homepage, no React/Streamlit yet

`api/home.py` emits HTML + CSS + small vanilla JS. Brief allows Streamlit or React later; current choice keeps Milestone UI deployable without a frontend stack.

### AI behind a provider interface; OpenAI only in one module

- `ExplanationProvider` protocol in `ai/contracts.py`
- `OpenAIExplanationProvider` is the only OpenAI-specific module (`responses.create`, model default `gpt-5.6-luna`, `store=False`, strict `json_schema`)
- Prompt version constant: `PROMPT_VERSION = "explain-v1"`
- Cache key: `(document_id, prompt_version)` in `document_explanations`
- Model input limited to title, published date, source, category, importance, source URL, `clean_text`

### Config and secrets

- `MACRO_DESK_` env prefix via pydantic-settings; `.env` gitignored
- `.env.example` documents keys including optional `MACRO_DESK_OPENAI_API_KEY`
- OpenAI key empty → explanations disabled (`503` when unconfigured)

### Schema evolution without a migration framework

`initialize()` creates tables and uses `ALTER TABLE` + backfill helpers for `category` / `classification_reason` and `importance` / `importance_reason` on existing DBs. **To verify:** whether a formal migration tool is planned for production.

---

## 4. Challenges & Resolutions

Only challenges evidenced by brief, code, commits, or tests are listed.

### 4.1 Accessing RBI content without scraping / bypass

* **Problem:** RBI pages may use anti-bot protections; automated HTML collection is unsafe/out of scope.
* **Investigation:** Brief requires official feeds/PDFs/endpoints and forbids workarounds.
* **Root cause:** Product constraint, not a failed scrape attempt recorded in git.
* **Resolution:** Official RSS feeds only; conservative client; refuse non-retryable HTTP statuses; store RSS excerpt text.
* **Trade-off / lesson:** `clean_text` may be thinner than the full linked document; explanations must declare that limitation.

### 4.2 Defining “what changed” for a personal desk

* **Problem:** Sorting/filtering only by RBI `published_at` does not describe what is new **to the local database** (e.g. after a catch-up ingest of older items).
* **Investigation:** Commit message and `list_first_seen_since` / `GET /changes` design.
* **Root cause:** Publish date and first-seen date answer different questions.
* **Resolution:** Persist `created_at` at insert; change window and homepage use `created_at`; record `ingest_runs` with counts/errors.
* **Trade-off / lesson:** An empty homepage can mean “no recent ingest,” even if RBI published recently—or conversely, a large catch-up ingest can flood the 24h window with older publications. Operators must understand the metric.

### 4.3 Adding classification without blocking ingest on an LLM

* **Problem:** Need filterable categories early; brief also wants later LLM/RAG workflows.
* **Investigation:** Commit `b5e03b5`; classifier as a single replaceable function.
* **Root cause:** Premature LLM classification would add cost, flakiness, and weaker testability for MVP filtering.
* **Resolution:** Keyword taxonomy + `classification_reason`; DB backfill for older rows; API category filter.
* **Trade-off / lesson:** Keyword rules misclassify edge cases (see tests for expected mappings); accuracy is rule quality, not model quality.

### 4.4 Multi-feed ingest without duplicating pipeline logic

* **Problem:** Notifications (then speeches) needed distinct labels but same fetch/parse/dedupe behavior.
* **Investigation:** Commit `ab5e2d2` / `5033a67`; `sources.py` `FeedSpec`.
* **Root cause:** Copy-pasting per-source pipelines would diverge error handling and dedupe.
* **Resolution:** One `ingest_feed` + `configured_feeds`; global uniqueness still applies across feeds.
* **Trade-off / lesson:** Cross-feed URL/hash collisions skip inserts; tests cover cross-source dedupe.

### 4.5 Schema growth on an already-initialized SQLite file

* **Problem:** Classification and importance columns were added after early `documents` rows existed.
* **Investigation:** `_ensure_*_columns` + `_backfill_*` in `db/repository.py`.
* **Root cause:** No external migration runner in Milestone 1.
* **Resolution:** Idempotent `ALTER` if missing; backfill null/empty fields via the same domain functions used at ingest.
* **Trade-off / lesson:** Fine for a personal SQLite file; may need explicit migrations before multi-environment deploy. **To verify** production migration strategy.

### 4.6 Keeping LLM integration swappable and cacheable

* **Problem:** Brief requires replaceable LLM calls, structured output, evidence, and prompt versioning.
* **Investigation:** Commit `758f77b`; `ai/contracts.py`, `service.py`, `openai_provider.py`, `tests/test_explanations.py`.
* **Root cause:** Scattering OpenAI calls would couple the API to one vendor and complicate prompt changes.
* **Resolution:** Provider protocol; OpenAI confined to one file; cache by `(document_id, prompt_version)`; `source_url` stored from the document (not trusted from the model); homepage expands an editorial note via `POST /documents/{id}/explanation`.
* **Trade-off / lesson:** Changing `PROMPT_VERSION` intentionally misses old cache rows (regenerate UX not implemented). No bulk/auto explanation job.

### 4.7 Import boundary between `ai` and `db`

* **Problem:** `DocumentRepository` persists `CachedExplanation` / `ExplanationDraft` types defined under `ai`, while `ai.service` imports `DocumentRepository`.
* **Investigation:** Visible in imports: `db/repository.py` → `macro_desk.ai.contracts`; `ai/service.py` → `macro_desk.db.repository`; `ai/__init__.py` re-exports contracts only (does not import `service` at package init).
* **Root cause:** Package `__init__` eagerly importing the service layer would create a circular import with the repository.
* **Resolution:** Keep `ai/__init__.py` thin; routes/app import `service` / providers explicitly.
* **Trade-off / lesson:** Domain explanation DTOs live under `ai` rather than `domain`. **To verify** whether moving shared models to `domain` is desired later.

---

## 5. AI / LLM Integration

### What exists

- On-demand explanation for **one** stored document
- Endpoint: `POST /documents/{document_id}/explanation`
- UI: `<details>` “Explain why this matters” under each homepage item; fetch on open; render with `textContent` (no HTML injection of model output)

### Architecture

```text
UI / API
  → explain_document (ai/service.py)
      → cache lookup (document_explanations)
      → ExplanationProvider.generate (protocol)
          → OpenAIExplanationProvider (Responses API)
      → save_explanation
```

### Provider / API details (as coded)

- Model setting: `MACRO_DESK_OPENAI_MODEL` default `gpt-5.6-luna`
- `client.responses.create(..., store=False, text.format.type=json_schema, strict=True)`
- Schema fields: `what_changed`, `why_it_matters`, `who_should_care`, `evidence_snippets`, `limitation_note`
- App trims evidence snippets to at most 3 after parse
- Errors: `ExplanationConfigError` → HTTP 503; `ExplanationProviderError` → HTTP 502

### Caching / persistence

- Table `document_explanations`
- Unique `(document_id, prompt_version)`
- FK to `documents(id)` with `ON DELETE CASCADE`
- Stores structured fields + `source_url` + `created_at`
- Repeat calls return `cached: true` without another model call
- No regenerate endpoint yet

### Prompt versioning

- Constant `PROMPT_VERSION = "explain-v1"` in `ai/contracts.py`
- Instructions live in `openai_provider.py` (`_INSTRUCTIONS`): use only provided fields; excerpt may not be full document; do not invent unsupported transmission effects

### Testing

- `tests/test_explanations.py`: fake provider proves single model call then cache; 404/503/502 paths; payload field allow-list; mocked Responses API shape (`store=False`, strict schema); homepage includes explain action
- Suite does **not** call the live OpenAI API

### Current limitations (from code/README/brief alignment)

- Uses RSS excerpt only; no linked-page scrape, web search, or embeddings
- No chat UI, no bulk explain, no Daily Macro Brief generation
- No evaluation harness for hallucination rate yet (brief Phase 5)
- Provider swap is interface-ready; only OpenAI implemented

---

## 6. Data Ingestion

### Sources (configured)

| Source label | `document_type` | Default URL |
| --- | --- | --- |
| RBI Press Releases | `press_release` | `https://rbi.org.in/pressreleases_rss.xml` |
| RBI Notifications | `notification` | `https://rbi.org.in/notifications_rss.xml` |
| RBI Speeches | `speech` | `https://rbi.org.in/speeches_rss.xml` |

Triggers: `POST /ingest`, CLI `python -m macro_desk.cli ingest` → `ingest_configured_feeds`.

### Fetch / parse

- Sequential one GET per feed
- `parse_rss`: RSS 2.0 `channel/item` → title, link, description, pubDate
- `parse_pub_date`: email-style dates; naive → UTC
- HTML description stripped via `domain/text.html_to_text`

### Document storage (`documents`)

Notable columns: title, `published_at`, source, `source_url`, `document_type`, `raw_text`, `clean_text`, `content_hash`, category, `classification_reason`, importance, `importance_reason`, `created_at`.

### Timestamps

- `published_at`: from RSS `pubDate` (or “now” if missing/unparseable)
- `created_at`: insert time (first-seen); timezone-aware UTC ISO strings in SQLite

### Deduplication

- Pre-check `exists_by_source_url` / `exists_by_content_hash`
- `content_hash` from normalized title + clean text (`domain/hashing.py`)
- Insert `IntegrityError` → treat as skip
- Global across feeds

### Ingest runs

- Table `ingest_runs`: started/finished, fetched/inserted/skipped/failed, errors JSON
- Recorded by `ingest_configured_feeds` (not by the press-only helper alone)

### Behavior notes

- Idempotent re-runs skip existing URLs/hashes
- Failures on one feed still allow later feeds in the loop; counts merge into one run record
- Tests inject RSS XML; production network is out of scope for pytest

---

## 7. Testing & Verification

Tests collected under `tests/` (approximate counts from modules):

| Module | Focus |
| --- | --- |
| `test_hashing.py` | Content hash stability / normalization |
| `test_deduplication.py` | URL/hash skips; cross-feed dedupe |
| `test_persistence.py` | Insert/read; classification/importance fields |
| `test_classification.py` | Taxonomy keyword mappings and reasons |
| `test_importance.py` | high/medium/low ranking rules |
| `test_changes.py` | First-seen window; ingest run recording |
| `test_api.py` | Health, filters (`category`, `document_type`, `importance`), ingest with injected feed |
| `test_home.py` | Empty state; lists first-seen items; speeches; high before newer low |
| `test_explanations.py` | Cache, errors, provider contract, homepage affordance |

Conventions:

- Temporary SQLite via `tmp_path` fixture
- No live network in tests
- Explanation tests inject a fake provider or monkeypatch `OpenAI`

**To verify:** exact pytest pass count on a clean CI runner (local collection historically ~59 tests as of tip `758f77b`).

---

## 8. Current State

### Works today

- Ingest three official RBI RSS feeds into SQLite
- Deduped storage with classification + importance
- API: `/health`, `/documents` (filters), `/ingest`, `/changes`, `/`, `/documents/{id}/explanation`
- Homepage: 24h first-seen list, importance ordering, explain expandable note
- Optional OpenAI explanations with SQLite cache keyed by prompt version
- CLI ingest
- Automated tests with mocked feeds/providers

### Incomplete relative to the brief

- Daily Macro Brief generation
- Embeddings / vector retrieval / RAG over passages
- Event extraction pipeline beyond keyword category/importance
- MOSPI / MoF and news tiers
- Streamlit/React dashboard, Docker, cloud deploy, scheduled ingest job
- Evaluation set / hallucination metrics
- Explanation regenerate UX
- Learning layer / concept glossary UI

### Known limitations

- Explanations and stored text are RSS-excerpt-bound
- Homepage empty when nothing has `created_at` in the last 24 hours (by design)
- README intro text lags multi-source + AI features
- Keyword classification/importance can be wrong on ambiguous titles
- Single-user SQLite assumptions

---

## 9. Next Milestones

Only items clearly supported by the brief and current direction (not speculative V2 fluff):

1. **Harden individual explanations** — review quality/grounding before expanding AI surface area (brief: evidence-traceable generation; explanations already defer Daily Brief).
2. **Daily Macro Brief (structured, source-grounded)** — primary product output in the brief; deferred until per-item explanations are useful.
3. **Embeddings + retrieval** — brief Phase 3; README already names Postgres/vector store as likely later step.
4. **Scheduled ingestion + deployment** — brief Phase 5 / deployment target (Docker, health, secrets, public URL).
5. **Evaluation** — brief requires measuring unsupported claims / usefulness; not started in code.
6. **Optional UI upgrade** — brief allows Streamlit or lightweight React after core pipeline works.

Do **not** start broad V2 (news triangulation, email bots, stance trackers, etc.) before MVP brief + deploy, per brief §14.

---

## 10. Interview Notes

Stories/decisions grounded in this repo that map well to DS / ML Eng interviews:

1. **Source-grounded AI vs chatbot** — product is change detection + structured explanation with evidence and limitation notes, not free-form chat.
2. **RSS-first ingestion under access constraints** — designing around anti-bot policy; excerpt vs full document trade-off.
3. **Idempotent data engineering** — dual uniqueness (`source_url`, content hash), ingest run metrics, injected-feed tests.
4. **First-seen semantics** — why `created_at` powers “what changed” for a personal system; operational implications for catch-up ingest.
5. **Rules before models** — taxonomy + importance as transparent, testable, replaceable functions; LLM deferred until filtering/ranking existed.
6. **Provider interface + prompt version cache** — vendor isolation, structured Outputs / Responses API, cache invalidation via `PROMPT_VERSION`, `store=False`.
7. **Strict structured output** — JSON schema with `additionalProperties: false`; trim evidence client-side; persist `source_url` from DB not model.
8. **SQLite-first pragmatism** — when not to introduce Postgres/pgvector; repository boundary for later swap.
9. **Test strategy for LLM features** — mock provider to prove cache behavior and HTTP error mapping without spending tokens in CI.
10. **Incremental architecture** — git shows feed generalization (`FeedSpec`) instead of three divergent scrapers.

Prep prompts for interviews:

- Walk through one document from RSS GET → row in `documents` → homepage → cached explanation.
- Explain what you would measure before trusting Daily Brief generation.
- How you would migrate SQLite → Postgres without rewriting domain models.

---

## Appendix A — API surface (as of tip)

- `GET /`
- `GET /health`
- `GET /documents` (`limit`, `category`, `document_type`, `importance`)
- `POST /ingest`
- `GET /changes` (`hours`, `limit`)
- `POST /documents/{document_id}/explanation`

## Appendix B — Git milestone map

```text
29954b4 init brief
9a0b61a Python 3.12 app + press-release ingest
b5e03b5 classification
ab5e2d2 notifications feed
b96eae5 first-seen changes + ingest_runs
c7e5171 homepage
5033a67 speeches feed
7ab1e13 importance ranking
758f77b on-demand explanations
```

## Appendix C — Gaps that cannot be fully reconstructed from the repo

- Exact operational incidents (empty homepage after Sep 7, live ingest of 30 items, live OpenAI E2E timings) are **not** recorded in git; treat those as session notes unless later committed here.
- Why Python **3.12** specifically (vs 3.11) beyond `requires-python = ">=3.12"`: **To verify**.
- Whether any failed scrape/HTML approaches were tried before RSS: **not evidenced** in history (design appears RSS-first from first code commit).
- Production/staging deployment history: **none in repo**.
- Human evaluation scores for explanations or classifiers: **none in repo**.
