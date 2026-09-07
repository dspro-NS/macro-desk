from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from macro_desk.api.app import create_app
from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository, connect, initialize
from macro_desk.ingestion.pipeline import ingest_configured_feeds
from tests.helpers import make_document

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def test_first_seen_window_includes_recent_and_excludes_older(
    repository: DocumentRepository,
) -> None:
    older = repository.insert(
        make_document(
            title="Older first seen",
            source_url="https://www.rbi.org.in/pr?id=old",
            content_hash="a1" + "b" * 62,
        ),
        created_at=NOW - timedelta(hours=48),
    )
    newer = repository.insert(
        make_document(
            title="Newer first seen",
            source_url="https://www.rbi.org.in/pr?id=new",
            content_hash="a2" + "b" * 62,
        ),
        created_at=NOW - timedelta(hours=2),
    )
    boundary = repository.insert(
        make_document(
            title="Exactly 24 hours ago",
            source_url="https://www.rbi.org.in/pr?id=edge",
            content_hash="a3" + "b" * 62,
        ),
        created_at=NOW - timedelta(hours=24),
    )
    assert older is not None
    assert newer is not None
    assert boundary is not None

    changed = repository.list_first_seen_since(NOW - timedelta(hours=24))
    titles = [item.title for item in changed]
    assert "Newer first seen" in titles
    assert "Exactly 24 hours ago" in titles
    assert "Older first seen" not in titles


def test_first_seen_uses_insert_time_not_rbi_publish_date(
    repository: DocumentRepository,
) -> None:
    stored = repository.insert(
        make_document(
            title="Old RBI date, new to us",
            published_at=NOW - timedelta(days=10),
            source_url="https://www.rbi.org.in/pr?id=lag",
            content_hash="a4" + "b" * 62,
        ),
        created_at=NOW - timedelta(hours=1),
    )
    assert stored is not None
    changed = repository.list_first_seen_since(NOW - timedelta(hours=24))
    assert [item.title for item in changed] == ["Old RBI date, new to us"]


def test_configured_ingest_persists_run_results(settings, repository: DocumentRepository) -> None:
    payload = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>PRESS RELEASES FROM RBI</title>
    <item>
      <title><![CDATA[Window item]]></title>
      <description><![CDATA[<p>Body</p>]]></description>
      <link>https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=500</link>
      <pubDate>Mon, 07 Sep 2026 10:00:00</pubDate>
    </item>
  </channel>
</rss>
""".encode("utf-8")

    def fetch(url: str) -> bytes:
        if "notification" in url:
            return """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>NOTIFICATIONS FROM RBI</title></channel></rss>
""".encode("utf-8")
        return payload

    result = ingest_configured_feeds(settings, repository, fetch=fetch)
    runs = repository.list_ingest_runs_since(datetime.now(timezone.utc) - timedelta(days=1))
    assert result.inserted == 1
    assert len(runs) == 1
    assert runs[0].fetched == 1
    assert runs[0].inserted == 1
    assert runs[0].skipped == 0
    assert runs[0].failed == 0
    assert runs[0].started_at <= runs[0].finished_at


def test_changes_endpoint_defaults_to_last_24_hours(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        repository = DocumentRepository(connection)
        repository.insert(
            make_document(
                title="Inside window",
                source_url="https://www.rbi.org.in/pr?id=in",
                content_hash="c1" + "d" * 62,
            ),
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        repository.insert(
            make_document(
                title="Outside window",
                source_url="https://www.rbi.org.in/pr?id=out",
                content_hash="c2" + "d" * 62,
            ),
            created_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        repository.record_ingest_run(
            started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            finished_at=datetime.now(timezone.utc) - timedelta(minutes=4),
            fetched=2,
            inserted=1,
            skipped=1,
            failed=0,
        )
    finally:
        connection.close()

    client = TestClient(create_app(settings))
    response = client.get("/changes")
    assert response.status_code == 200
    body = response.json()
    assert body["hours"] == 24
    titles = [item["title"] for item in body["items"]]
    assert titles == ["Inside window"]
    assert set(body["items"][0]) == {
        "title",
        "source",
        "category",
        "published_at",
        "source_url",
    }
    assert body["items"][0]["source_url"].startswith("https://www.rbi.org.in/")
    assert len(body["ingest_runs"]) == 1
    assert body["ingest_runs"][0]["inserted"] == 1


def test_changes_endpoint_honours_shorter_window(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        repository = DocumentRepository(connection)
        repository.insert(
            make_document(
                title="Three hours ago",
                source_url="https://www.rbi.org.in/pr?id=3h",
                content_hash="c3" + "d" * 62,
            ),
            created_at=datetime.now(timezone.utc) - timedelta(hours=3),
        )
    finally:
        connection.close()

    client = TestClient(create_app(settings))
    wide = client.get("/changes", params={"hours": 24})
    narrow = client.get("/changes", params={"hours": 1})
    assert [item["title"] for item in wide.json()["items"]] == ["Three hours ago"]
    assert narrow.json()["items"] == []
    assert narrow.json()["hours"] == 1
