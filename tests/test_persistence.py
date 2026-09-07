from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from macro_desk.db.repository import DocumentRepository, connect, initialize
from tests.helpers import make_document


def test_insert_and_fetch_document(repository: DocumentRepository) -> None:
    stored = repository.insert(make_document())
    assert stored is not None
    assert stored.id is not None
    assert stored.title == "RBI press release"
    fetched = repository.get_by_id(stored.id)
    assert fetched is not None
    assert fetched.content_hash == stored.content_hash
    assert fetched.source_url == stored.source_url
    assert fetched.category == stored.category
    assert fetched.classification_reason
    assert fetched.importance == stored.importance
    assert fetched.importance_reason


def test_list_newest_can_filter_by_category(repository: DocumentRepository) -> None:
    repository.insert(
        make_document(
            title="Minutes of the Monetary Policy Committee Meeting",
            clean_text="The MPC kept the policy repo rate unchanged.",
            source_url="https://www.rbi.org.in/pr?id=10",
            content_hash="e" * 64,
        )
    )
    repository.insert(
        make_document(
            title="Enhancement of UPI transaction limits",
            clean_text="Limits on the Unified Payments Interface have been enhanced.",
            source_url="https://www.rbi.org.in/pr?id=11",
            content_hash="f" * 64,
        )
    )
    payments = repository.list_newest(category="Payments")
    assert [item.title for item in payments] == ["Enhancement of UPI transaction limits"]
    assert payments[0].category == "Payments"


def test_list_newest_can_filter_by_document_type(repository: DocumentRepository) -> None:
    repository.insert(
        make_document(
            title="Press item",
            source="RBI Press Releases",
            document_type="press_release",
            source_url="https://www.rbi.org.in/pr?id=30",
            content_hash="7" * 64,
        )
    )
    repository.insert(
        make_document(
            title="Notification item",
            source="RBI Notifications",
            document_type="notification",
            source_url="https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=30",
            content_hash="8" * 64,
        )
    )
    notifications = repository.list_newest(document_type="notification")
    assert [item.title for item in notifications] == ["Notification item"]
    assert notifications[0].source == "RBI Notifications"


def test_list_newest_first(repository: DocumentRepository) -> None:
    older = make_document(
        title="Older",
        source_url="https://www.rbi.org.in/pr?id=1",
        content_hash="b" * 64,
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = make_document(
        title="Newer",
        source_url="https://www.rbi.org.in/pr?id=2",
        content_hash="c" * 64,
        published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    repository.insert(older)
    repository.insert(newer)

    titles = [item.title for item in repository.list_newest(limit=10)]
    assert titles == ["Newer", "Older"]


def test_initialize_classifies_legacy_rows(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.sqlite"
    legacy = sqlite3.connect(database_path)
    legacy.execute(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            published_at TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT NOT NULL,
            document_type TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            clean_text TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    legacy.execute(
        """
        INSERT INTO documents (
            title, published_at, source, source_url, document_type,
            raw_text, clean_text, content_hash, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Minutes of the Monetary Policy Committee Meeting",
            "2026-08-01T00:00:00+00:00",
            "RBI Press Releases",
            "https://www.rbi.org.in/pr?id=legacy",
            "press_release",
            "raw",
            "The MPC kept the policy repo rate unchanged.",
            "3" * 64,
            "2026-08-01T00:00:00+00:00",
        ),
    )
    legacy.commit()
    legacy.close()

    connection = connect(database_path)
    try:
        initialize(connection)
        stored = DocumentRepository(connection).list_newest()[0]
        assert stored.category == "Monetary Policy"
        assert stored.classification_reason
    finally:
        connection.close()
