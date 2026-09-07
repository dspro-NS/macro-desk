from fastapi.testclient import TestClient

from macro_desk.api.app import create_app
from macro_desk.config import Settings


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
