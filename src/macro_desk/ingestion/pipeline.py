from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository
from macro_desk.domain.classification import DocumentClassifier, classify_document
from macro_desk.domain.hashing import compute_content_hash, normalize_whitespace
from macro_desk.domain.importance import DocumentImportanceRanker, rank_importance
from macro_desk.domain.models import NewDocument
from macro_desk.domain.text import html_to_text
from macro_desk.ingestion.client import FeedClient, FeedFetchError
from macro_desk.ingestion.rss import parse_pub_date, parse_rss
from macro_desk.ingestion.sources import FeedSpec, configured_feeds

logger = logging.getLogger(__name__)

FetchFn = Callable[[str], bytes]


@dataclass
class IngestResult:
    fetched: int = 0
    inserted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: "IngestResult") -> "IngestResult":
        self.fetched += other.fetched
        self.inserted += other.inserted
        self.skipped += other.skipped
        self.failed += other.failed
        self.errors.extend(other.errors)
        return self


def ingest_feed(
    settings: Settings,
    repository: DocumentRepository,
    feed: FeedSpec,
    fetch: Optional[FetchFn] = None,
    classifier: Optional[DocumentClassifier] = None,
    ranker: Optional[DocumentImportanceRanker] = None,
) -> IngestResult:
    """Idempotent ingest of one official RSS feed.

    Makes a single HTTP GET unless a fetch function is injected (tests).
    Does not scrape HTML pages or attempt to bypass access controls.
    """
    result = IngestResult()
    fetch_fn = fetch or FeedClient(
        timeout_seconds=settings.http_timeout_seconds,
        user_agent=settings.user_agent,
    ).fetch

    try:
        xml_bytes = fetch_fn(feed.url)
    except FeedFetchError as exc:
        logger.error("Ingestion aborted for %s: %s", feed.url, exc)
        result.failed = 1
        result.errors.append("{}: {}".format(feed.url, exc))
        return result
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected fetch failure for %s", feed.url)
        result.failed = 1
        result.errors.append("{}: {}".format(feed.url, exc))
        return result

    try:
        items = parse_rss(xml_bytes)
    except ValueError as exc:
        logger.error("Could not parse RSS feed %s: %s", feed.url, exc)
        result.failed = 1
        result.errors.append("{}: {}".format(feed.url, exc))
        return result

    result.fetched = len(items)
    for item in items:
        try:
            _persist_item(feed, repository, item, result, classifier, ranker)
        except Exception as exc:
            logger.exception("Failed to persist %s", item.source_url)
            result.failed += 1
            result.errors.append("{}: {}".format(item.source_url, exc))

    logger.info(
        "Ingest complete source=%s fetched=%s inserted=%s skipped=%s failed=%s",
        feed.source_name,
        result.fetched,
        result.inserted,
        result.skipped,
        result.failed,
    )
    return result


def ingest_configured_feeds(
    settings: Settings,
    repository: DocumentRepository,
    fetch: Optional[FetchFn] = None,
    classifier: Optional[DocumentClassifier] = None,
    ranker: Optional[DocumentImportanceRanker] = None,
) -> IngestResult:
    """Ingest each configured official feed sequentially, one GET per feed."""
    started_at = datetime.now(timezone.utc)
    combined = IngestResult()
    for feed in configured_feeds(settings):
        combined.merge(
            ingest_feed(
                settings,
                repository,
                feed,
                fetch=fetch,
                classifier=classifier,
                ranker=ranker,
            )
        )
    repository.record_ingest_run(
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        fetched=combined.fetched,
        inserted=combined.inserted,
        skipped=combined.skipped,
        failed=combined.failed,
        errors=combined.errors,
    )
    return combined


def ingest_rbi_press_releases(
    settings: Settings,
    repository: DocumentRepository,
    fetch: Optional[FetchFn] = None,
    classifier: Optional[DocumentClassifier] = None,
    ranker: Optional[DocumentImportanceRanker] = None,
) -> IngestResult:
    """Backward-compatible helper for the press-release feed only."""
    press_release_feed = configured_feeds(settings)[0]
    return ingest_feed(
        settings,
        repository,
        press_release_feed,
        fetch=fetch,
        classifier=classifier,
        ranker=ranker,
    )


def _persist_item(
    feed: FeedSpec,
    repository: DocumentRepository,
    item,
    result: IngestResult,
    classifier: Optional[DocumentClassifier],
    ranker: Optional[DocumentImportanceRanker],
) -> None:
    clean_text = html_to_text(item.raw_text) or normalize_whitespace(item.title)
    content_hash = compute_content_hash(item.title, clean_text)

    if repository.exists_by_source_url(item.source_url) or repository.exists_by_content_hash(content_hash):
        result.skipped += 1
        logger.debug("Skipping duplicate %s", item.source_url)
        return

    classification = classify_document(item.title, clean_text, classifier=classifier)
    importance = rank_importance(item.title, clean_text, ranker=ranker)
    document = NewDocument(
        title=normalize_whitespace(item.title),
        published_at=parse_pub_date(item.published_at),
        source=feed.source_name,
        source_url=item.source_url,
        document_type=feed.document_type,
        raw_text=item.raw_text,
        clean_text=clean_text,
        content_hash=content_hash,
        category=classification.category,
        classification_reason=classification.reason,
        importance=importance.importance,
        importance_reason=importance.reason,
    )
    stored = repository.insert(document)
    if stored is None:
        result.skipped += 1
        return
    result.inserted += 1
