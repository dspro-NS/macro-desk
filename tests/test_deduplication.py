from macro_desk.db.repository import DocumentRepository
from macro_desk.ingestion.pipeline import ingest_configured_feeds, ingest_rbi_press_releases
from macro_desk.ingestion.sources import (
    DOCUMENT_TYPE_NOTIFICATION,
    DOCUMENT_TYPE_PRESS_RELEASE,
    DOCUMENT_TYPE_SPEECH,
)
from tests.helpers import make_document

SAMPLE_PRESS_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>PRESS RELEASES FROM RBI</title>
    <item>
      <title><![CDATA[First item]]></title>
      <description><![CDATA[<p>Alpha text</p>]]></description>
      <link>https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=1</link>
      <pubDate>Fri, 04 Sep 2026 17:00:00</pubDate>
    </item>
    <item>
      <title><![CDATA[Second item]]></title>
      <description><![CDATA[<p>Beta text</p>]]></description>
      <link>https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=2</link>
      <pubDate>Thu, 03 Sep 2026 17:00:00</pubDate>
    </item>
  </channel>
</rss>
""".encode("utf-8")

SAMPLE_NOTIFICATION_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>NOTIFICATIONS FROM RBI</title>
    <item>
      <title><![CDATA[Master Direction on KYC]]></title>
      <description><![CDATA[<p>Know Your Customer Direction.</p>]]></description>
      <link>https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=1&amp;Mode=0</link>
      <pubDate>Sat, 05 Sep 2026 17:00:00</pubDate>
    </item>
  </channel>
</rss>
""".encode("utf-8")

SAMPLE_SPEECH_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>SPEECHES FROM RBI</title>
    <item>
      <title><![CDATA[Governor's speech on monetary policy]]></title>
      <description><![CDATA[<p>A speech on the policy stance.</p>]]></description>
      <link>https://www.rbi.org.in/scripts/BS_SpeechesView.aspx?id=1575</link>
      <pubDate>Wed, 03 Sep 2026 14:30:00</pubDate>
    </item>
  </channel>
</rss>
""".encode("utf-8")

SAMPLE_RSS = SAMPLE_PRESS_RSS


def _feed_payload(url: str) -> bytes:
    if "notification" in url:
        return SAMPLE_NOTIFICATION_RSS
    if "speech" in url:
        return SAMPLE_SPEECH_RSS
    return SAMPLE_PRESS_RSS


def test_duplicate_source_url_is_not_inserted(repository: DocumentRepository) -> None:
    first = repository.insert(make_document())
    duplicate = repository.insert(
        make_document(content_hash="d" * 64, title="Changed title")
    )
    assert first is not None
    assert duplicate is None
    assert repository.list_newest()[0].title == "RBI press release"


def test_duplicate_content_hash_is_not_inserted(repository: DocumentRepository) -> None:
    first = repository.insert(make_document())
    duplicate = repository.insert(
        make_document(
            source_url="https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=99",
            title="Different title that still uses same hash field",
        )
    )
    assert first is not None
    assert duplicate is None


def test_pipeline_skips_duplicates_without_network(settings, repository: DocumentRepository) -> None:
    first = ingest_rbi_press_releases(settings, repository, fetch=lambda url: SAMPLE_RSS)
    second = ingest_rbi_press_releases(settings, repository, fetch=lambda url: SAMPLE_RSS)

    assert first.fetched == 2
    assert first.inserted == 2
    assert first.skipped == 0
    assert second.inserted == 0
    assert second.skipped == 2
    assert second.failed == 0
    assert [item.title for item in repository.list_newest()] == ["First item", "Second item"]
    assert all(item.category == "Other" for item in repository.list_newest())


def test_configured_feeds_ingest_press_releases_notifications_and_speeches(
    settings, repository: DocumentRepository
) -> None:
    result = ingest_configured_feeds(settings, repository, fetch=_feed_payload)

    assert result.fetched == 4
    assert result.inserted == 4
    assert result.skipped == 0
    assert result.failed == 0

    by_title = {item.title: item for item in repository.list_newest()}
    assert by_title["First item"].document_type == DOCUMENT_TYPE_PRESS_RELEASE
    assert by_title["First item"].source == "RBI Press Releases"
    assert by_title["Master Direction on KYC"].document_type == DOCUMENT_TYPE_NOTIFICATION
    assert by_title["Master Direction on KYC"].source == "RBI Notifications"
    assert by_title["Governor's speech on monetary policy"].document_type == DOCUMENT_TYPE_SPEECH
    assert by_title["Governor's speech on monetary policy"].source == "RBI Speeches"
    assert (
        by_title["Governor's speech on monetary policy"].source_url
        == "https://www.rbi.org.in/scripts/BS_SpeechesView.aspx?id=1575"
    )

    speeches = repository.list_newest(document_type=DOCUMENT_TYPE_SPEECH)
    assert [item.title for item in speeches] == ["Governor's speech on monetary policy"]


def test_duplicate_content_is_skipped_across_feeds(settings, repository: DocumentRepository) -> None:
    overlapping_notification = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>NOTIFICATIONS FROM RBI</title>
    <item>
      <title><![CDATA[First item]]></title>
      <description><![CDATA[<p>Alpha text</p>]]></description>
      <link>https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=99&amp;Mode=0</link>
      <pubDate>Sat, 05 Sep 2026 17:00:00</pubDate>
    </item>
  </channel>
</rss>
""".encode("utf-8")

    def fetch(url: str) -> bytes:
        if "notification" in url:
            return overlapping_notification
        if "speech" in url:
            return SAMPLE_SPEECH_RSS
        return SAMPLE_PRESS_RSS

    result = ingest_configured_feeds(settings, repository, fetch=fetch)
    assert result.inserted == 3
    assert result.skipped == 1
    titles = [item.title for item in repository.list_newest()]
    assert titles.count("First item") == 1
    assert "Second item" in titles
    assert "Governor's speech on monetary policy" in titles
