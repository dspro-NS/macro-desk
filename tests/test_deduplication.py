from macro_desk.db.repository import DocumentRepository
from macro_desk.ingestion.pipeline import ingest_rbi_press_releases
from tests.helpers import make_document

SAMPLE_RSS = """<?xml version="1.0" encoding="utf-8"?>
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
