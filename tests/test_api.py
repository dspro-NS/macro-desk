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

