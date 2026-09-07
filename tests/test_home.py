from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from macro_desk.api.app import create_app
from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository, connect, initialize
from tests.helpers import make_document


def test_home_shows_empty_state_when_nothing_is_new(settings: Settings) -> None:
    client = TestClient(create_app(settings))
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Nothing new in the last 24 hours." in response.text
    assert "<ol" not in response.text


def test_home_lists_latest_updates_from_existing_data(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        repository = DocumentRepository(connection)
        repository.insert(
            make_document(
                title="Minutes of the Monetary Policy Committee Meeting",
                clean_text="The MPC kept the policy repo rate unchanged.",
                source="RBI Press Releases",
                source_url="https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=88",
                content_hash="aa" + "b" * 62,
                published_at=datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc),
            ),
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        repository.insert(
            make_document(
                title="Should not appear on the homepage",
                source_url="https://www.rbi.org.in/pr?id=old-home",
                content_hash="cc" + "d" * 62,
            ),
            created_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
    finally:
        connection.close()

    client = TestClient(create_app(settings))
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "Minutes of the Monetary Policy Committee Meeting" in html
    assert "RBI Press Releases" in html
    assert "Monetary Policy" in html
    assert "2026-09-06" in html
    assert "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=88" in html
    assert "RBI source" in html
    assert "Should not appear on the homepage" not in html
    assert "Nothing new in the last 24 hours." not in html


def test_home_shows_speech_source_and_link(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        DocumentRepository(connection).insert(
            make_document(
                title="Governor's speech on monetary policy",
                source="RBI Speeches",
                document_type="speech",
                source_url="https://www.rbi.org.in/scripts/BS_SpeechesView.aspx?id=1575",
                content_hash="ee" + "f" * 62,
                published_at=datetime(2026, 9, 3, 14, 30, tzinfo=timezone.utc),
            ),
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
    finally:
        connection.close()

    html = TestClient(create_app(settings)).get("/").text
    assert "speech on monetary policy" in html
    assert "RBI Speeches" in html
    assert "https://www.rbi.org.in/scripts/BS_SpeechesView.aspx?id=1575" in html
    assert "RBI source" in html
