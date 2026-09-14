from __future__ import annotations

import json

from fastapi.testclient import TestClient

from macro_desk.ai.contracts import (
    PROMPT_VERSION,
    ExplanationDraft,
    ExplanationItem,
    ExplanationProviderError,
    QuizQuestion,
    normalize_revision_draft,
)
from macro_desk.ai.openai_provider import OpenAIExplanationProvider
from macro_desk.ai.service import item_from_document
from macro_desk.api.app import create_app
from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository, connect, initialize
from tests.helpers import make_document


def sample_draft(**overrides) -> ExplanationDraft:
    payload = {
        "what_happened": [
            "RBI amended priority-sector lending classification rules in the stored excerpt.",
            "The change affects how banks classify eligible lending.",
        ],
        "primary_concept_name": "Priority Sector Lending (PSL)",
        "primary_concept_explanation": [
            "Concept: PSL directs a share of bank credit toward underserved sectors.",
            "Why it exists: so credit is not allocated only by commercial preference.",
            "Key distinction: eligibility rules and the credit base jointly shape compliance.",
        ],
        "how_it_works": [
            "Step 1 → Banks meet PSL targets against a credit base.",
            "Step 2 → Classification rules decide what lending counts toward the target.",
        ],
        "related_concepts": [
            {
                "name": "ANBC",
                "explanation": "Adjusted Net Bank Credit is a common base for PSL targets.",
                "why_relevant": "Target percentages apply to a credit base such as ANBC.",
            }
        ],
        "why_this_matters": [
            "If what qualifies as PSL changes, banks may reallocate lending.",
            "Newly eligible categories can attract more target-seeking credit.",
            "Newly ineligible categories can lose that compliance incentive.",
        ],
        "source_backed_facts": [],
        "limitation_note": "The RSS excerpt does not state quantitative target changes.",
        "quiz": [
            {
                "question": "If what counts toward PSL eligibility expands, what is the most likely bank response, all else equal?",
                "options": [
                    "Banks may reallocate lending toward newly eligible categories to meet targets",
                    "The policy repo rate automatically falls",
                    "CRR is abolished for all deposits",
                ],
                "correct_option_index": 0,
                "explanation": "PSL is a credit-allocation constraint; changing eligibility changes how banks can meet the target.",
            },
            {
                "question": "Why can a lending base such as ANBC matter for PSL?",
                "options": [
                    "Targets are often expressed relative to a credit base, so the base shapes the absolute amount required",
                    "It replaces monetary policy entirely",
                    "It is only used for FX reserves accounting",
                ],
                "correct_option_index": 0,
                "explanation": "Percentage targets need a denominator; changing the base changes compliance arithmetic.",
            },
        ],
        "remember_this": [
            "PSL steers bank credit toward underserved sectors.",
            "Eligibility and the credit base jointly determine how banks meet PSL targets.",
            "An amendment is a rule change; quantified credit shifts need more than the excerpt.",
        ],
    }
    payload.update(overrides)
    return ExplanationDraft.model_validate(payload)


class FakeExplanationProvider:
    def __init__(self, draft: ExplanationDraft | None = None) -> None:
        self.calls: list[ExplanationItem] = []
        self.draft = draft or sample_draft()

    def generate(self, item: ExplanationItem) -> ExplanationDraft:
        self.calls.append(item)
        return self.draft


def _insert_sample(settings: Settings) -> int:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        stored = DocumentRepository(connection).insert(
            make_document(
                title="Priority Sector Lending amendment directions",
                clean_text="RBI issued third amendment directions on priority sector lending targets.",
                source_url="https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=13698&Mode=0",
                content_hash="e1" + "a" * 62,
            )
        )
    finally:
        connection.close()
    assert stored is not None and stored.id is not None
    return stored.id


def test_prompt_version_is_concept_revision_v5() -> None:
    assert PROMPT_VERSION == "concept-revision-v5"


def test_revision_uses_cached_result_on_repeat(settings: Settings) -> None:
    document_id = _insert_sample(settings)
    provider = FakeExplanationProvider()
    client = TestClient(create_app(settings, explanation_provider=provider))

    first = client.post("/documents/{}/explanation".format(document_id))
    second = client.post("/documents/{}/explanation".format(document_id))

    assert first.status_code == 200
    assert second.status_code == 200
    body = first.json()
    assert body["cached"] is False
    assert second.json()["cached"] is True
    assert body["prompt_version"] == PROMPT_VERSION
    assert body["primary_concept_name"] == "Priority Sector Lending (PSL)"
    assert body["what_happened"] == second.json()["what_happened"]
    assert len(body["quiz"]) == 2
    assert body["quiz"][0]["correct_option_index"] == 0
    assert len(body["remember_this"]) >= 2
    assert body["source_url"].endswith("Id=13698&Mode=0")
    assert len(provider.calls) == 1
    assert set(provider.calls[0].model_dump()) == {
        "title",
        "published_at",
        "source",
        "category",
        "importance",
        "source_url",
        "clean_text",
    }


def test_revision_allows_omitted_optional_sections(settings: Settings) -> None:
    document_id = _insert_sample(settings)
    draft = sample_draft(how_it_works=[], related_concepts=[])
    client = TestClient(
        create_app(settings, explanation_provider=FakeExplanationProvider(draft))
    )
    response = client.post("/documents/{}/explanation".format(document_id))
    assert response.status_code == 200
    body = response.json()
    assert body["how_it_works"] == []
    assert body["related_concepts"] == []
    assert body["what_happened"]
    assert isinstance(body["what_happened"], list)
    assert body["primary_concept_name"]
    assert body["why_this_matters"]
    assert len(body["quiz"]) >= 2
    assert len(body["remember_this"]) >= 2
    section_ids = [section["id"] for section in body["sections"]]
    assert section_ids == [
        "what_happened",
        "concept",
        "why_it_matters",
        "recall",
    ]
    assert "how_it_works" not in section_ids
    assert "connections" not in section_ids
    for section in body["sections"]:
        assert section["title"]
        assert section["kind"] in {"bullets", "concept", "connections", "quiz"}


def test_build_revision_sections_omits_empty_optional_content() -> None:
    from macro_desk.ai.sections import build_revision_sections

    draft = sample_draft(how_it_works=[], related_concepts=[])
    sections = build_revision_sections(draft)
    assert [section.id for section in sections] == [
        "what_happened",
        "concept",
        "why_it_matters",
        "recall",
    ]
    full = build_revision_sections(sample_draft())
    assert [section.id for section in full] == [
        "what_happened",
        "concept",
        "how_it_works",
        "connections",
        "why_it_matters",
        "recall",
    ]
    assert full[0].kind == "bullets"
    assert len(full[0].bullets) >= 2
    assert full[1].kind == "concept"
    assert full[1].eyebrow
    assert len(full[1].bullets) >= 2
    assert full[2].kind == "bullets"
    assert full[-1].kind == "quiz"
    assert len(full[-1].quiz) >= 2


def test_normalize_revision_clamps_quiz_and_related_concepts() -> None:
    draft = sample_draft(
        what_happened=["a", "b", "c", "d", "e", "f"],
        primary_concept_explanation=["a", "b", "c", "d", "e", "f"],
        how_it_works=["a", "b", "c", "d", "e", "f"],
        why_this_matters=["a", "b", "c", "d", "e", "f"],
        related_concepts=[
            {"name": "A", "explanation": "a", "why_relevant": "x"},
            {"name": "B", "explanation": "b", "why_relevant": "x"},
            {"name": "C", "explanation": "c", "why_relevant": "x"},
            {"name": "D", "explanation": "d", "why_relevant": "x"},
            {"name": "E", "explanation": "e", "why_relevant": "x"},
        ],
        source_backed_facts=["fact one", "fact two", "fact three"],
        quiz=[
            {
                "question": "Q1",
                "options": ["a", "b", "c", "d", "e"],
                "correct_option_index": 1,
                "explanation": "because",
            },
            {
                "question": "Q2",
                "options": ["a", "b"],
                "correct_option_index": 0,
                "explanation": "because",
            },
            {
                "question": "Q3",
                "options": ["a", "b"],
                "correct_option_index": 0,
                "explanation": "because",
            },
            {
                "question": "Q4",
                "options": ["a", "b"],
                "correct_option_index": 0,
                "explanation": "because",
            },
        ],
        remember_this=["one", "two", "three", "four", "five"],
    )
    normalized = normalize_revision_draft(draft)
    assert len(normalized.what_happened) == 5
    assert len(normalized.primary_concept_explanation) == 5
    assert len(normalized.how_it_works) == 5
    assert len(normalized.why_this_matters) == 5
    assert len(normalized.related_concepts) == 3
    assert len(normalized.source_backed_facts) == 1
    assert len(normalized.quiz) == 3
    assert len(normalized.quiz[0].options) == 4
    assert len(normalized.remember_this) == 4


def test_home_revision_ui_is_concept_first_not_fact_list(settings: Settings) -> None:
    from datetime import datetime, timezone

    connection = connect(settings.database_path)
    try:
        initialize(connection)
        stored = DocumentRepository(connection).insert(
            make_document(content_hash="h2" + "c" * 62),
            created_at=datetime.now(timezone.utc),
        )
    finally:
        connection.close()
    assert stored is not None
    html = TestClient(create_app(settings)).get("/").text
    assert "Revise the concepts" not in html
    assert "From this RBI item" not in html
    assert "--color-bg" in html or "--page" in html
    assert "notebook" in html
    assert "section-nav" in html
    assert "data.sections" in html
    assert "rev-bullets" in html
    assert "renderBullets" in html
    assert "pill-category" in html
    assert "view-notebook" in html
    assert "update-open" in html
    assert "Neha's own notebook" in html


def test_revision_endpoint_returns_structured_sections(settings: Settings) -> None:
    document_id = _insert_sample(settings)
    client = TestClient(
        create_app(settings, explanation_provider=FakeExplanationProvider())
    )
    body = client.post("/documents/{}/explanation".format(document_id)).json()
    assert body["sections"][0]["title"] == "What happened?"
    assert body["sections"][0]["kind"] == "bullets"
    assert isinstance(body["sections"][0]["bullets"], list)
    assert len(body["sections"][0]["bullets"]) >= 2
    concept = next(section for section in body["sections"] if section["id"] == "concept")
    assert concept["kind"] == "concept"
    assert concept["bullets"]
    recall = next(section for section in body["sections"] if section["id"] == "recall")
    assert recall["kind"] == "quiz"
    assert len(recall["quiz"]) >= 2
    assert "correct_option_index" in recall["quiz"][0]


def test_malformed_draft_is_rejected() -> None:
    try:
        ExplanationDraft.model_validate(
            {
                "what_happened": [],
                "primary_concept_name": "PSL",
                "primary_concept_explanation": ["credit steering"],
                "how_it_works": [],
                "related_concepts": [],
                "why_this_matters": ["banks reallocate"],
                "source_backed_facts": [],
                "limitation_note": "",
                "quiz": [],
                "remember_this": [],
            }
        )
        assert False, "expected validation error"
    except ValueError:
        pass


def test_quiz_index_must_match_options() -> None:
    try:
        QuizQuestion(
            question="Q",
            options=["a", "b"],
            correct_option_index=5,
            explanation="x",
        )
        assert False, "expected validation error"
    except Exception:
        pass


def test_explanation_returns_404_for_unknown_document(settings: Settings) -> None:
    client = TestClient(create_app(settings, explanation_provider=FakeExplanationProvider()))
    response = client.post("/documents/999/explanation")
    assert response.status_code == 404


def test_explanation_returns_503_when_unconfigured(settings: Settings) -> None:
    document_id = _insert_sample(settings)
    client = TestClient(create_app(settings, explanation_provider=None))
    response = client.post("/documents/{}/explanation".format(document_id))
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_explanation_returns_502_when_provider_fails(settings: Settings) -> None:
    document_id = _insert_sample(settings)

    class FailingProvider:
        def generate(self, item: ExplanationItem) -> ExplanationDraft:
            raise ExplanationProviderError("failed")

    client = TestClient(create_app(settings, explanation_provider=FailingProvider()))
    response = client.post("/documents/{}/explanation".format(document_id))
    assert response.status_code == 502


def test_item_from_document_sends_only_allowed_fields(settings: Settings) -> None:
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        stored = DocumentRepository(connection).insert(make_document())
    finally:
        connection.close()
    assert stored is not None
    item = item_from_document(stored)
    assert "raw_text" not in item.model_dump()
    assert "classification_reason" not in item.model_dump()


def test_openai_provider_uses_concept_revision_schema(monkeypatch) -> None:
    captured: dict = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)

            class Result:
                output_text = json.dumps(sample_draft().model_dump())

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
            published_at="2026-09-11",
            source="RBI Notifications",
            category="Liquidity",
            importance="high",
            source_url="https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=13698&Mode=0",
            clean_text="Third amendment directions on priority sector lending.",
        )
    )
    assert captured["model"] == "gpt-5.6-luna"
    assert captured["store"] is False
    assert captured["text"]["format"]["name"] == "rbi_concept_revision"
    assert captured["text"]["format"]["strict"] is True
    assert captured["text"]["format"]["schema"]["required"]
    assert draft.primary_concept_name.startswith("Priority Sector")
    assert len(draft.quiz) >= 2


def test_openai_instructions_require_mechanism_teaching() -> None:
    from macro_desk.ai import openai_provider

    text = openai_provider._INSTRUCTIONS
    assert "EACH SECTION ANSWERS A DIFFERENT QUESTION" in text
    assert "STRUCTURED BULLETS" in text
    assert "ONE IDEA = ONE BULLET" in text
    assert "Do NOT reteach" in text or "Do NOT reteach definition" in text or "APPLY the concept" in text
    assert "meta-disclaimers" in text or "defensive/meta" in text
    assert "same causal chain not repeated" in text.lower() or "ONCE" in text
    assert "UPSC" in text
    assert "why_this_matters" in text
    assert "3–5 minutes" in text or "~3–5 minutes" in text


def test_openai_provider_rejects_incomplete_quiz(monkeypatch) -> None:
    class FakeResponses:
        def create(self, **kwargs):
            class Result:
                output_text = json.dumps(
                    sample_draft(
                        quiz=[
                            {
                                "question": "Only one question",
                                "options": ["a", "b"],
                                "correct_option_index": 0,
                                "explanation": "thin",
                            }
                        ]
                    ).model_dump()
                )

            return Result()

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr("macro_desk.ai.openai_provider.OpenAI", FakeClient)
    provider = OpenAIExplanationProvider(api_key="test-key", model="gpt-5.6-luna")
    try:
        provider.generate(
            ExplanationItem(
                title="Test",
                published_at="2026-09-11",
                source="RBI Notifications",
                category="Liquidity",
                importance="high",
                source_url="https://www.rbi.org.in/x",
                clean_text="Excerpt",
            )
        )
        assert False, "expected provider error"
    except ExplanationProviderError:
        pass


def test_home_opens_notebook_from_update_card(settings: Settings) -> None:
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
    assert "Revise the concepts" not in html
    assert "Explain why this matters" not in html
    assert 'data-document-id="{}"'.format(stored.id) in html
    assert "update-open" in html
    assert "nb-gutter" in html
    assert "nb-coil" not in html
    assert "createCoilUnit" not in html


def test_old_prompt_version_does_not_satisfy_new_cache(settings: Settings) -> None:
    document_id = _insert_sample(settings)
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        connection.execute(
            """
            INSERT INTO document_explanations (
                document_id, prompt_version, what_changed, why_it_matters,
                who_should_care, evidence_snippets, limitation_note,
                source_url, created_at, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                "explain-v1",
                "old",
                "old",
                "old",
                "[]",
                "",
                "https://example.com",
                "2026-09-14T00:00:00+00:00",
                None,
            ),
        )
        connection.commit()
    finally:
        connection.close()

    provider = FakeExplanationProvider()
    client = TestClient(create_app(settings, explanation_provider=provider))
    response = client.post("/documents/{}/explanation".format(document_id))
    assert response.status_code == 200
    assert response.json()["prompt_version"] == "concept-revision-v5"
    assert response.json()["cached"] is False
    assert len(provider.calls) == 1
