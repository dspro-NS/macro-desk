# India Economic Brief — Project Journal

Living engineering journal for India Economic Brief. Entries below are reconstructed from the repository, git history, `README.md`, `rbi_macro_intelligence_project_brief_v2.md`, source code, and tests. Items that cannot be confirmed from those artifacts are marked **To verify**.

Last reconstructed from working tree after concept-revision redesign (prior tip included `5c00c4b` journal + `758f77b` explanations).

---

## 1. Project Goal

India Economic Brief is a personal **India macro and RBI intelligence** system. The project brief (`rbi_macro_intelligence_project_brief_v2.md`) frames the product around answering:

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

### Product pivot: document explanation → concept revision

India Economic Brief’s intended daily use is: open the desk in the morning, see important fresh RBI/macro developments, and use each development as a **trigger to strengthen fundamentals**—not to consume another news summary.

**Why document explanation (`explain-v1`) was insufficient**

- It answered “what changed / why it matters / who should care” for one item.
- That improved reading of the update, but did not reliably rebuild the underlying concept (e.g. PSL vs ANBC as a denominator).
- It risked feeling like a generic summarizer rather than a learning loop.

**Why concept revision fits India Economic Brief better**

- Update → primary concept → mechanism (if needed) → sparse related concepts → implications → active recall → takeaways.
- Educational fundamentals may go beyond the excerpt; update-specific claims stay source-grounded and limited.
- Designed for ~3–5 minutes, adaptive depth, clarity over completeness—not an exam portal or long article.

**Decisions on brevity, adaptive depth, and active recall**

- Prompt/schema version evolved: `concept-revision-v1` → `v2` → `v3` → `v4` → **`concept-revision-v5`** (does **not** redefine `explain-v1`).
- Optional sections (`how_it_works`, `related_concepts`) use empty arrays when omitted.
- Conceptual teaching fields are **structured bullet arrays** (content ≠ presentation); the UI renders lists.
- Default quiz: 2–3 conceptual MCQs with short post-answer explanations (active recall, not a question bank).
- UI action: **Revise the concepts**; progressive disclosure; interactive quiz in-page.

**Refinement (`concept-revision-v2`): shift center of gravity off the document**

The first concept-revision version still felt too document-centric—especially a “From this RBI item” fact list that competed with the source link the user already has. This pass deliberately:

- treats `what_happened` as the only place for source update facts;
- prefers `source_backed_facts=[]` and **removes that section from the UI**;
- reframes headings around the learning hierarchy (concept → mechanism → connections → implications → recall);
- asks for causal bridges in related concepts, not glossary dumps;
- prefers reasoning MCQs (“if X changes, what follows?”) over excerpt trivia;
- keeps `remember_this` to a ~20-second mental model (≤4 bullets);
- bumps prompt version so old v1 caches are not silently reused.

**Refinement (`concept-revision-v3`): definitions → mechanism teaching**

Even after v2, drafts could still read like correct-sounding summaries/definitions (“what the term means”) rather than teaching the user how to reason. Prompt-only refinement (no schema/UI/architecture change):

- ask “what is actually happening underneath?”;
- require mechanism (who decides, incentives, trade-offs, what could go wrong);
- use selective BEFORE→AFTER contrasts for policy/regulatory shifts;
- prefer explicit causal chains over topic lists;
- distinguish easy-to-confuse pairs when useful;
- use short concrete examples when abstraction stays vague;
- make `why_this_matters` an analytical chain (change → behaviour/constraint → effect → who);
- MCQs must require the mechanism just taught;
- `remember_this` compresses the mental model, not earlier prose;
- internal quality gate in the prompt before returning;
- bump to v3 so prior caches regenerate.

**UI milestone: full progressive disclosure + content/UI separation**

Revision content is assembled into typed `RevisionSection` objects (`ai/sections.py`) and returned as `sections` on the explanation API. The homepage JS maps over those sections as editorial accordions (`rev-section`), all collapsed by default—no hard-coded RBI prose in the frontend. Optional empty sections are omitted. Design tokens (`--color-*`, `--font-*`) centralize palette/typography so later visual iteration does not require hunting through components. Goal: refine prompts/content without repeatedly rewriting the UI.

**Refinement (`concept-revision-v5`): paragraphs → structured bullets + HTML title cleanup**

Daily revision prose was too paragraph-heavy for a morning learning loop. Large blocks raise cognitive load; the product needs scannable editorial briefs (one idea per bullet, usually 1–2 sentences, ~2–5 bullets per conceptual section)—not an exam-prep notes dump and not markdown bullets stuffed into strings.

- Schema/prompt bumped to **`concept-revision-v5`**.
- `what_happened`, `primary_concept_explanation`, `how_it_works`, `why_this_matters` are **string arrays**.
- `RevisionSection` carries `bullets: list[str]` for conceptual kinds (`bullets` / `concept`); quiz and connections stay typed structures.
- UI renders `<ul class="rev-bullets">` from those arrays (comfortable spacing, light indentation); accordion shell unchanged.
- Structured content keeps future prompt/content refinement independent of CSS/JS presentation.

Separately, RBI RSS titles/descriptions can contain HTML such as `<sup>1</sup>`. Escaping on the homepage made tags visible (`Decade<sup>1</sup>`). Fix at the normalization boundary—not a template-only patch:

- `domain/text.py`: `html_to_text` / `sanitize_plain_text` skip `sup`/`sub` (and script/style) content so footnote markers are dropped for titles/metadata.
- Ingest (`pipeline._persist_item`) sanitizes titles before hash/classify/store.
- Repository `_row_to_document` sanitizes title/`clean_text` on read for older dirty rows.
- AI `item_from_document` re-sanitizes title and `clean_text` before model input.
- Tests: `tests/test_text.py` (footnote example + common tags); explanation tests assert structured `sections[].bullets` and `rev-bullets` in the homepage JS.

**UI milestone: intelligence notebook (homepage + revision)**

Presentation-only redesign in `api/home.py` (no API/schema/prompt/ingest/DB changes). Goal: a calm morning notebook—editorial list → spiral two-page revision—not a dashboard or exam portal.

Homepage:
- Soft ivory page with very low-contrast pastel-wave atmosphere (CSS radial gradients / blurred pseudo-elements).
- Hero: “India Economic Brief” + “Good morning. Let’s see what’s moving in the Indian economy.”
- “Latest updates” reading list: document type / domain / importance pills, dominant title, short supporting line from `clean_text`, date, “Revise the concepts →”, RBI source link.
- Clicking an update opens an in-page notebook view (same `/` route; still `POST /documents/{id}/explanation`).

Notebook:
- Article header (metadata + title + source).
- Left page: all six learning sections with subtle tone accents; only the active item is tinted.
- Right page: structured bullets / connections / quiet recall MCQs from API `sections`; optional Key takeaway from `remember_this`.
- Desktop two-page layout with minimal spiral rings; mobile stacks and hides the spine.
- Titles continue to use `sanitize_plain_text` before render.

**Product rename: Macro Desk → India Economic Brief**

User-facing product brand renamed to **India Economic Brief**. Internal Python package/module path `macro_desk`, env prefix `MACRO_DESK_`, SQLite paths, and technical User-Agent (`MacroDesk/…`) remain unchanged so imports, config, and ingestion identity stay stable.

### What exists

- On-demand concept revision for **one** stored document
- Endpoint: `POST /documents/{document_id}/explanation` (same path; new response schema)
- UI: homepage reading list → in-page spiral notebook; fetch on open; render with DOM `textContent` / buttons (no unsanitized HTML of model output)

### Architecture

```text
UI / API
  → explain_document (ai/service.py)
      → cache lookup (document_explanations by document_id + prompt version)
      → ExplanationProvider.generate (protocol)
          → OpenAIExplanationProvider (Responses API)
      → save_explanation (JSON payload + mirrored legacy columns)
```

### Provider / API details (as coded)

- Model setting: `MACRO_DESK_OPENAI_MODEL` default `gpt-5.6-luna`
- `client.responses.create(..., store=False, text.format.type=json_schema, strict=True, name=rbi_concept_revision)`
- Core fields: `what_happened` (bullets), `primary_concept_name`, `primary_concept_explanation` (bullets), `why_this_matters` (bullets), `quiz`, `remember_this`
- Optional: `how_it_works` (bullets or `[]`), `related_concepts`, `source_backed_facts`, `limitation_note`
- App normalizes: ≤5 bullets per conceptual list, ≤3 related concepts, ≤3 quiz items (≤1 source fact), ≤4 options, ≤4 takeaways
- Errors: `ExplanationConfigError` → HTTP 503; `ExplanationProviderError` → HTTP 502

### Caching / persistence

- Table `document_explanations`
- Unique `(document_id, prompt_version)`
- Full revision JSON in `payload` column (added via `ALTER` for existing DBs)
- Legacy text columns mirrored for inspectability (`what_changed` ← `what_happened`, etc.)
- Old `explain-v1` rows do not satisfy `concept-revision-v1` cache lookups
- Repeat calls return `cached: true` without another model call
- No regenerate endpoint yet

### Prompt versioning

- Constant `PROMPT_VERSION = "concept-revision-v5"` in `ai/contracts.py`
- Instructions in `openai_provider.py`: structured bullets, distinct section responsibilities, anti-repetition, analytical application of today's update, minimal meta-disclaimers, mechanism teaching, quality gate

### Testing

- `tests/test_explanations.py`: schema/version, optional sections, bullet arrays, normalize clamps, malformed output, quiz index validation, cache, 404/503/502, provider mock, instruction quality asserts, old version isolation, homepage “Revise the concepts” + bullet rendering hooks
- `tests/test_text.py`: HTML→plain sanitization (footnotes/superscripts and common tags)
- Suite does **not** call the live OpenAI API
- Local suite as of structured bullets + HTML sanitization: **76 passed**

### Current limitations

- Uses RSS excerpt for update-specific facts; fundamentals may be broader conceptual knowledge
- No chat UI, no bulk revise, no Daily Macro Brief generation
- No evaluation harness for hallucination / pedagogy quality yet
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
- HTML description/title stripped via `domain/text.html_to_text` / `sanitize_plain_text` (footnote `<sup>`/`<sub>` content dropped for product plain text)

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
| `test_explanations.py` | Cache, errors, provider contract, structured bullets/sections, homepage affordance |
| `test_text.py` | HTML→plain sanitization for titles/excerpts |

Conventions:

- Temporary SQLite via `tmp_path` fixture
- No live network in tests
- Explanation tests inject a fake provider or monkeypatch `OpenAI`

**To verify:** exact pytest pass count on a clean CI runner (local collection historically **76 passed** after structured bullets + HTML sanitization).

---

## 8. Current State

### Works today

- Ingest three official RBI RSS feeds into SQLite
- Deduped storage with classification + importance
- API: `/health`, `/documents` (filters), `/ingest`, `/changes`, `/`, `/documents/{id}/explanation`
- Homepage: editorial 24h first-seen list → in-page spiral notebook revision (six-section nav + bullet teaching)
- Optional OpenAI concept revisions (`concept-revision-v5`) with SQLite cache
- Title/excerpt HTML sanitization at ingest + read + AI input boundaries
- CLI ingest
- Automated tests with mocked feeds/providers

### Incomplete relative to the brief

- Daily Macro Brief generation
- Embeddings / vector retrieval / RAG over passages
- Event extraction pipeline beyond keyword category/importance
- MOSPI / MoF and news tiers
- Streamlit/React dashboard, Docker, cloud deploy, scheduled ingest job
- Evaluation set / hallucination / pedagogy metrics
- Revision regenerate UX
- Standalone concept glossary / spaced repetition

### Known limitations

- Update-specific claims are RSS-excerpt-bound; concept teaching may use broader established knowledge
- Homepage empty when nothing has `created_at` in the last 24 hours (by design)
- Keyword classification/importance can be wrong on ambiguous titles
- Single-user SQLite assumptions

---

## 9. Next Milestones

Only items clearly supported by the brief and current direction (not speculative V2 fluff):

1. **Harden concept revisions** — review brevity, grounding, and quiz quality on real daily items before expanding AI surface area.
2. **Daily Macro Brief (structured, source-grounded)** — primary product output in the brief; still deferred until per-item revisions are consistently useful.
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
