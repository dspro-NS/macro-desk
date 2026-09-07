from datetime import datetime, timezone

from macro_desk.db.repository import DocumentRepository
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
