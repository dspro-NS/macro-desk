from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from macro_desk.api.app import create_app
from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository, connect, initialize
from tests.helpers import make_document


def test_home_strips_trailing_hyphen_from_titles(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        DocumentRepository(connection).insert(
            make_document(
                title="Keynote Address, August 19, 2026 -",
                source_url="https://www.rbi.org.in/scripts/BS_SpeechesView.aspx?Id=trail-hyphen",
                content_hash="th" + "y" * 62,
            ),
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
    finally:
        connection.close()

    html = TestClient(create_app(settings)).get("/").text
    assert "Keynote Address, August 19, 2026" in html
    assert "2026 -" not in html
    assert "2026-</" not in html


def test_home_strips_html_markup_from_titles(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        DocumentRepository(connection).insert(
            make_document(
                title="Getting ready for the next Decade<sup>1</sup> - Keynote",
                source_url="https://www.rbi.org.in/scripts/BS_SpeechesView.aspx?Id=html-title",
                content_hash="ht" + "m" * 62,
            ),
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
    finally:
        connection.close()

    html = TestClient(create_app(settings)).get("/").text
    assert "Getting ready for the next Decade - Keynote" in html
    assert "<sup>" not in html
    assert "</sup>" not in html


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
    assert "Press release" in html
    assert "Monetary Policy" in html
    assert "2026-09-06" in html
    assert "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=88" in html
    assert "RBI source" in html
    assert "Should not appear on the homepage" not in html
    assert "Nothing new in the last 24 hours." not in html
    assert "India Economic Brief" in html
    assert "Good morning" in html
    assert "Latest updates" in html


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
    assert "Speech" in html
    assert "https://www.rbi.org.in/scripts/BS_SpeechesView.aspx?id=1575" in html
    assert "RBI source" in html


def test_home_lists_high_importance_before_newer_low_items(settings: Settings) -> None:
    now = datetime.now(timezone.utc)
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        repository = DocumentRepository(connection)
        repository.insert(
            make_document(
                title="Result of Variable Rate Repo Auction",
                source_url="https://www.rbi.org.in/pr?id=low-home",
                content_hash="31" + "a" * 62,
            ),
            created_at=now - timedelta(hours=1),
        )
        repository.insert(
            make_document(
                title="Minutes of the Monetary Policy Committee Meeting",
                clean_text="The MPC kept the policy repo rate unchanged.",
                source_url="https://www.rbi.org.in/pr?id=high-home",
                content_hash="32" + "a" * 62,
            ),
            created_at=now - timedelta(hours=8),
        )
    finally:
        connection.close()

    html = TestClient(create_app(settings)).get("/").text
    high_at = html.find("Monetary Policy Committee")
    low_at = html.find("Variable Rate Repo Auction")
    assert high_at != -1 and low_at != -1
    assert high_at < low_at
    assert "high" in html
    assert "low" in html
