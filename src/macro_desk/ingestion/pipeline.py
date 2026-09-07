from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository
from macro_desk.domain.classification import DocumentClassifier, classify_document
from macro_desk.domain.hashing import compute_content_hash, normalize_whitespace
from macro_desk.domain.models import NewDocument
from macro_desk.domain.text import html_to_text
from macro_desk.ingestion.client import FeedClient, FeedFetchError
from macro_desk.ingestion.rss import parse_pub_date, parse_rss

logger = logging.getLogger(__name__)

FetchFn = Callable[[str], bytes]


@dataclass
class IngestResult:
    fetched: int = 0
    inserted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def ingest_rbi_press_releases(
    settings: Settings,
    repository: DocumentRepository,
    fetch: Optional[FetchFn] = None,
    classifier: Optional[DocumentClassifier] = None,
) -> IngestResult:
    """Idempotent ingest of the configured official RBI RSS feed.

    Makes a single HTTP GET unless a fetch function is injected (tests).
    Does not scrape HTML pages or attempt to bypass access controls.
    """
    result = IngestResult()
    fetch_fn = fetch or FeedClient(
        timeout_seconds=settings.http_timeout_seconds,
        user_agent=settings.user_agent,
    ).fetch

    try:
        xml_bytes = fetch_fn(settings.rbi_rss_url)
    except FeedFetchError as exc:
        logger.error("Ingestion aborted: %s", exc)
        result.failed = 1
        result.errors.append(str(exc))
        return result
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected fetch failure for %s", settings.rbi_rss_url)
        result.failed = 1
        result.errors.append(str(exc))
        return result

    try:
        items = parse_rss(xml_bytes)
    except ValueError as exc:
        logger.error("Could not parse RSS feed: %s", exc)
        result.failed = 1
        result.errors.append(str(exc))
        return result

    result.fetched = len(items)
    for item in items:
        try:
            _persist_item(settings, repository, item, result, classifier)
        except Exception as exc:
            logger.exception("Failed to persist %s", item.source_url)
            result.failed += 1
            result.errors.append("{}: {}".format(item.source_url, exc))

    logger.info(
        "Ingest complete fetched=%s inserted=%s skipped=%s failed=%s",
        result.fetched,
        result.inserted,
        result.skipped,
        result.failed,
    )
    return result


def _persist_item(
    settings: Settings,
    repository: DocumentRepository,
    item,
    result: IngestResult,
    classifier: Optional[DocumentClassifier],
) -> None:
    clean_text = html_to_text(item.raw_text) or normalize_whitespace(item.title)
    content_hash = compute_content_hash(item.title, clean_text)

    if repository.exists_by_source_url(item.source_url) or repository.exists_by_content_hash(content_hash):
        result.skipped += 1
        logger.debug("Skipping duplicate %s", item.source_url)
        return

    classification = classify_document(item.title, clean_text, classifier=classifier)
    document = NewDocument(
        title=normalize_whitespace(item.title),
        published_at=parse_pub_date(item.published_at),
        source=settings.source_name,
        source_url=item.source_url,
        document_type=settings.document_type,
        raw_text=item.raw_text,
        clean_text=clean_text,
        content_hash=content_hash,
        category=classification.category,
        classification_reason=classification.reason,
    )
    stored = repository.insert(document)
    if stored is None:
        result.skipped += 1
        return
    result.inserted += 1
