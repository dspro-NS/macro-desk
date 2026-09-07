# Macro Desk

Personal **India macro and RBI intelligence** system. Milestone 1 stores official RBI press releases. It does not summarise, embed, or generate briefs.

## Local setup

Python 3.12 or newer.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Optional: edit `.env`. Defaults already point at the official RBI press-release RSS feed and a local SQLite file.

## Environment variables

All settings use the `MACRO_DESK_` prefix.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MACRO_DESK_DATABASE_PATH` | `data/macro_desk.sqlite` | SQLite file path |
| `MACRO_DESK_RBI_RSS_URL` | `https://rbi.org.in/pressreleases_rss.xml` | Official RBI press-release RSS feed |
| `MACRO_DESK_HTTP_TIMEOUT_SECONDS` | `20` | HTTP timeout for the single RSS request |
| `MACRO_DESK_USER_AGENT` | MacroDesk/0.1 (project URL + purpose) | Identifiable client header |
| `MACRO_DESK_SOURCE_NAME` | `RBI Press Releases` | Stored `source` value |
| `MACRO_DESK_DOCUMENT_TYPE` | `press_release` | Stored document type |

Copy `.env.example` rather than committing secrets. This milestone has no API keys.

## Run the API

```bash
uvicorn macro_desk.main:app --reload
```

- `GET /health` — liveness
- `GET /documents?limit=50` — stored documents, newest first
- `GET /documents?category=Payments` — same list, filtered by taxonomy category
- `POST /ingest` — fetch the RSS feed once and persist new items

Categories are assigned with keyword rules on title and clean text (not an LLM). Each stored document includes `category` and `classification_reason`. The classifier is a single function, so it can be replaced later without changing storage or the API.

## Run ingestion from the CLI

```bash
python -m macro_desk.cli ingest
```

Each run performs **one** GET against the configured RSS URL, with a timeout and a clear error log if the feed is blocked, times out, or is invalid XML. Item bodies are taken from the RSS `description` field. The pipeline does not scrape linked HTML pages and does not attempt to bypass access controls, CAPTCHAs, or anti-bot responses (including HTTP 401/403/418/429).

Duplicates are skipped when the `source_url` or content hash already exists.

## Tests

Tests do not make network requests. The ingest pipeline is exercised with an injected RSS payload.

```bash
pytest
```

## Architecture: SQLite first

SQLite is the datastore for Milestone 1 because this is a single-user personal tool:

- Zero extra services to install or host
- The document store is one file, easy to inspect and back up
- Unique indexes on `source_url` and `content_hash` give idempotent inserts without a separate cache
- SQLAlchemy/Postgres would add operational cost before there is concurrent write load or a deployment target

PostgreSQL (and later a vector store) remains the likely production step when the app is deployed or when embeddings are added. The repository is a thin SQLite wrapper so that swap can happen without changing the domain model.

## Layout

```text
src/macro_desk/
  api/           FastAPI routes
  db/            SQLite connection and persistence
  domain/        Document model, hashing, HTML-to-text, keyword classification
  ingestion/     RSS fetch, parse, idempotent pipeline
tests/           hash, dedup, and persistence tests
```
