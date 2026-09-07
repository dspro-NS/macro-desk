from __future__ import annotations

from dataclasses import dataclass

from macro_desk.config import Settings

DOCUMENT_TYPE_PRESS_RELEASE = "press_release"
DOCUMENT_TYPE_NOTIFICATION = "notification"
DOCUMENT_TYPE_SPEECH = "speech"
DOCUMENT_TYPE_VALUES = (
    DOCUMENT_TYPE_PRESS_RELEASE,
    DOCUMENT_TYPE_NOTIFICATION,
    DOCUMENT_TYPE_SPEECH,
)

SOURCE_PRESS_RELEASES = "RBI Press Releases"
SOURCE_NOTIFICATIONS = "RBI Notifications"
SOURCE_SPEECHES = "RBI Speeches"


@dataclass(frozen=True)
class FeedSpec:
    """One official RSS feed. Ingestion is the same for every spec."""

    url: str
    source_name: str
    document_type: str


def configured_feeds(settings: Settings) -> tuple[FeedSpec, ...]:
    return (
        FeedSpec(
            url=settings.rbi_rss_url,
            source_name=SOURCE_PRESS_RELEASES,
            document_type=DOCUMENT_TYPE_PRESS_RELEASE,
        ),
        FeedSpec(
            url=settings.rbi_notification_rss_url,
            source_name=SOURCE_NOTIFICATIONS,
            document_type=DOCUMENT_TYPE_NOTIFICATION,
        ),
        FeedSpec(
            url=settings.rbi_speeches_rss_url,
            source_name=SOURCE_SPEECHES,
            document_type=DOCUMENT_TYPE_SPEECH,
        ),
    )
