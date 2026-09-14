from __future__ import annotations

import json

from fastapi.testclient import TestClient

from macro_desk.ai.contracts import (
    PROMPT_VERSION,
    ExplanationDraft,
    ExplanationItem,
    ExplanationProviderError,
)
from macro_desk.ai.openai_provider import OpenAIExplanationProvider
from macro_desk.ai.service import item_from_document
from macro_desk.api.app import create_app
from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository, connect, initialize
from tests.helpers import make_document


class FakeExplanationProvider:
    def __init__(self, draft: ExplanationDraft | None = None) -> None:
        self.calls: list[ExplanationItem] = []
        self.draft = draft or ExplanationDraft(
            what_changed="The excerpt says the repo rate was left unchanged.",
            why_it_matters="Policy transmission stays on hold only if that reading of the excerpt is correct.",
            who_should_care="Watchers of the policy rate and money-market conditions.",
            evidence_snippets=["Repo rate unchanged."],
            limitation_note="The stored RSS excerpt does not include the full circular.",
        )

    def generate(self, item: ExplanationItem) -> ExplanationDraft:
        self.calls.append(item)
        return self.draft


def _insert_sample(settings: Settings) -> int:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        stored = DocumentRepository(connection).insert(
            make_document(
                title="Minutes of the Monetary Policy Committee Meeting",
                clean_text="The MPC kept the policy repo rate unchanged.",
                source_url="https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=500",
                content_hash="e1" + "a" * 62,
            )
        )
    finally:
        connection.close()
    assert stored is not None and stored.id is not None
    return stored.id


def test_explanation_uses_cached_result_on_repeat(settings: Settings) -> None:
    document_id = _insert_sample(settings)
    provider = FakeExplanationProvider()
    client = TestClient(create_app(settings, explanation_provider=provider))

    first = client.post("/documents/{}/explanation".format(document_id))
    second = client.post("/documents/{}/explanation".format(document_id))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert first.json()["what_changed"] == second.json()["what_changed"]
    assert first.json()["source_url"].endswith("prid=500")
    assert first.json()["prompt_version"] == PROMPT_VERSION
    assert len(provider.calls) == 1
    payload = provider.calls[0].model_dump()
    assert set(payload) == {
        "title",
        "published_at",
        "source",
        "category",
        "importance",
        "source_url",
        "clean_text",
    }
    assert payload["clean_text"] == "The MPC kept the policy repo rate unchanged."


def test_explanation_returns_404_for_unknown_document(settings: Settings) -> None:
    client = TestClient(create_app(settings, explanation_provider=FakeExplanationProvider()))
    response = client.post("/documents/999/explanation")
    assert response.status_code == 404


def test_explanation_returns_503_when_unconfigured(settings: Settings) -> None:
    document_id = _insert_sample(settings)
    client = TestClient(create_app(settings, explanation_provider=None))
    response = client.post("/documents/{}/explanation".format(document_id))
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_explanation_returns_502_when_provider_fails(settings: Settings) -> None:
    document_id = _insert_sample(settings)

    class FailingProvider:
        def generate(self, item: ExplanationItem) -> ExplanationDraft:
            raise ExplanationProviderError("failed")

    client = TestClient(create_app(settings, explanation_provider=FailingProvider()))
    response = client.post("/documents/{}/explanation".format(document_id))
    assert response.status_code == 502
    assert "failed" in response.json()["detail"].lower()


def test_item_from_document_sends_only_allowed_fields(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        stored = DocumentRepository(connection).insert(make_document())
    finally:
        connection.close()
    assert stored is not None
    item = item_from_document(stored)
    assert item.source_url == stored.source_url
    assert item.clean_text == stored.clean_text
    assert "raw_text" not in item.model_dump()
    assert "classification_reason" not in item.model_dump()


def test_openai_provider_uses_responses_api_without_storing(monkeypatch) -> None:
    captured: dict = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            class Result:
                output_text = json.dumps(
                    {
                        "what_changed": "Rate unchanged.",
                        "why_it_matters": "The excerpt does not support a transmission conclusion.",
                        "who_should_care": "Rate watchers.",
                        "evidence_snippets": ["Repo rate unchanged.", "extra", "third", "fourth"],
                        "limitation_note": "RSS excerpt only.",
                    }
                )

            return Result()

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.responses = FakeResponses()

    monkeypatch.setattr("macro_desk.ai.openai_provider.OpenAI", FakeClient)
    provider = OpenAIExplanationProvider(api_key="test-key", model="gpt-5.6-luna")
    draft = provider.generate(
        ExplanationItem(
            title="Test",
            published_at="2026-09-04",
            source="RBI Press Releases",
            category="Monetary Policy",
            importance="high",
            source_url="https://www.rbi.org.in/pr?id=1",
            clean_text="Repo rate unchanged.",
        )
    )
    assert captured["model"] == "gpt-5.6-luna"
    assert captured["store"] is False
    assert captured["text"]["format"]["type"] == "json_schema"
    assert captured["text"]["format"]["strict"] is True
    assert captured["text"]["format"]["name"] == "rbi_item_explanation"
    assert "client_kwargs" in captured
    assert len(draft.evidence_snippets) == 3


def test_home_includes_explain_action(settings: Settings) -> None:
    from datetime import datetime, timezone

    connection = connect(settings.database_path)
    try:
        initialize(connection)
        stored = DocumentRepository(connection).insert(
            make_document(content_hash="h1" + "b" * 62),
            created_at=datetime.now(timezone.utc),
        )
    finally:
        connection.close()
    assert stored is not None and stored.id is not None
    html = TestClient(create_app(settings)).get("/").text
    assert "Explain why this matters" in html
    assert 'data-document-id="{}"'.format(stored.id) in html
    assert "/documents/" in html
    assert "explanation" in html
