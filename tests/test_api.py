from fastapi.testclient import TestClient

from macro_desk.api.app import create_app
from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository, connect, initialize
from tests.helpers import make_document


def test_health_endpoint(settings: Settings) -> None:
    client = TestClient(create_app(settings))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_documents_endpoint_empty(settings: Settings) -> None:
    client = TestClient(create_app(settings))
    response = client.get("/documents")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["items"] == []


def test_documents_can_be_filtered_by_category(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        repository = DocumentRepository(connection)
        repository.insert(
            make_document(
                title="Minutes of the Monetary Policy Committee Meeting",
                clean_text="The MPC kept the policy repo rate unchanged.",
                source_url="https://www.rbi.org.in/pr?id=20",
                content_hash="1" * 64,
            )
        )
        repository.insert(
            make_document(
                title="Enhancement of UPI transaction limits",
                clean_text="Limits on the Unified Payments Interface have been enhanced.",
                source_url="https://www.rbi.org.in/pr?id=21",
                content_hash="2" * 64,
            )
        )
    finally:
        connection.close()

    client = TestClient(create_app(settings))
    response = client.get("/documents", params={"category": "Payments"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["title"] == "Enhancement of UPI transaction limits"
    assert body["items"][0]["category"] == "Payments"
    assert body["items"][0]["classification_reason"]


def test_unknown_category_filter_is_rejected(settings: Settings) -> None:
    client = TestClient(create_app(settings))
    response = client.get("/documents", params={"category": "Stocks"})
    assert response.status_code == 400
    assert "Unknown category" in response.json()["detail"]


def test_documents_can_be_filtered_by_document_type(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        repository = DocumentRepository(connection)
        repository.insert(
            make_document(
                title="Press item",
                document_type="press_release",
                source="RBI Press Releases",
                source_url="https://www.rbi.org.in/pr?id=40",
                content_hash="9" * 64,
            )
        )
        repository.insert(
            make_document(
                title="Notification item",
                document_type="notification",
                source="RBI Notifications",
                source_url="https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=40",
                content_hash="0" * 64,
            )
        )
    finally:
        connection.close()

    client = TestClient(create_app(settings))
    response = client.get("/documents", params={"document_type": "notification"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["title"] == "Notification item"
    assert body["items"][0]["document_type"] == "notification"
    assert body["items"][0]["source"] == "RBI Notifications"


def test_documents_can_be_filtered_by_speech_type(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        repository = DocumentRepository(connection)
        repository.insert(
            make_document(
                title="Press item",
                document_type="press_release",
                source="RBI Press Releases",
                source_url="https://www.rbi.org.in/pr?id=41",
                content_hash="11" + "a" * 62,
            )
        )
        repository.insert(
            make_document(
                title="Governor's speech on monetary policy",
                document_type="speech",
                source="RBI Speeches",
                source_url="https://www.rbi.org.in/scripts/BS_SpeechesView.aspx?id=1575",
                content_hash="12" + "a" * 62,
            )
        )
    finally:
        connection.close()

    client = TestClient(create_app(settings))
    response = client.get("/documents", params={"document_type": "speech"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["title"] == "Governor's speech on monetary policy"
    assert body["items"][0]["document_type"] == "speech"
    assert body["items"][0]["source"] == "RBI Speeches"
    assert body["items"][0]["source_url"].endswith("BS_SpeechesView.aspx?id=1575")


def test_unknown_document_type_filter_is_rejected(settings: Settings) -> None:
    client = TestClient(create_app(settings))
    response = client.get("/documents", params={"document_type": "tender"})
    assert response.status_code == 400
    assert "Unknown document_type" in response.json()["detail"]


def test_documents_can_be_filtered_by_importance(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        repository = DocumentRepository(connection)
        repository.insert(
            make_document(
                title="Minutes of the Monetary Policy Committee Meeting",
                clean_text="The MPC kept the policy repo rate unchanged.",
                source_url="https://www.rbi.org.in/pr?id=50",
                content_hash="21" + "a" * 62,
            )
        )
        repository.insert(
            make_document(
                title="Result of Variable Rate Repo Auction",
                source_url="https://www.rbi.org.in/pr?id=51",
                content_hash="22" + "a" * 62,
            )
        )
    finally:
        connection.close()

    client = TestClient(create_app(settings))
    response = client.get("/documents", params={"importance": "high"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert "Monetary Policy Committee" in body["items"][0]["title"]
    assert body["items"][0]["importance"] == "high"
    assert body["items"][0]["importance_reason"]


def test_unknown_importance_filter_is_rejected(settings: Settings) -> None:
    client = TestClient(create_app(settings))
    response = client.get("/documents", params={"importance": "critical"})
    assert response.status_code == 400
    assert "Unknown importance" in response.json()["detail"]

