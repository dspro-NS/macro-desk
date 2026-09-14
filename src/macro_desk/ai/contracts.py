from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field, field_validator, model_validator


PROMPT_VERSION = "concept-revision-v5"

# OpenAI strict JSON Schema: every property listed is required.
# Optional UI sections use empty array when omitted.
# Conceptual teaching fields are string arrays (one idea per item)—not prose blobs.
_BULLET_ARRAY = {
    "type": "array",
    "items": {"type": "string"},
}

REVISION_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "what_happened": _BULLET_ARRAY,
        "primary_concept_name": {"type": "string"},
        "primary_concept_explanation": _BULLET_ARRAY,
        "how_it_works": _BULLET_ARRAY,
        "related_concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "explanation": {"type": "string"},
                    "why_relevant": {"type": "string"},
                },
                "required": ["name", "explanation", "why_relevant"],
                "additionalProperties": False,
            },
        },
        "why_this_matters": _BULLET_ARRAY,
        "source_backed_facts": {
            "type": "array",
            "items": {"type": "string"},
        },
        "limitation_note": {"type": "string"},
        "quiz": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "correct_option_index": {"type": "integer"},
                    "explanation": {"type": "string"},
                },
                "required": [
                    "question",
                    "options",
                    "correct_option_index",
                    "explanation",
                ],
                "additionalProperties": False,
            },
        },
        "remember_this": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "what_happened",
        "primary_concept_name",
        "primary_concept_explanation",
        "how_it_works",
        "related_concepts",
        "why_this_matters",
        "source_backed_facts",
        "limitation_note",
        "quiz",
        "remember_this",
    ],
    "additionalProperties": False,
}

# Backward-compatible alias used by older import sites during the redesign.
EXPLANATION_JSON_SCHEMA = REVISION_JSON_SCHEMA


class ExplanationItem(BaseModel):
    """Fields sent to the model. Nothing else from the stored document."""

    title: str
    published_at: str
    source: str
    category: str
    importance: str
    source_url: str
    clean_text: str


class RelatedConcept(BaseModel):
    name: str
    explanation: str
    why_relevant: str


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=2)
    correct_option_index: int
    explanation: str

    @model_validator(mode="after")
    def _index_in_range(self) -> "QuizQuestion":
        if not (0 <= self.correct_option_index < len(self.options)):
            raise ValueError("correct_option_index out of range for options")
        return self


def _clean_bullets(values: list[str]) -> list[str]:
    return [item.strip() for item in values if item and item.strip()]


class ExplanationDraft(BaseModel):
    """Concept revision payload for prompt version concept-revision-v5."""

    what_happened: list[str]
    primary_concept_name: str
    primary_concept_explanation: list[str]
    how_it_works: list[str] = Field(default_factory=list)
    related_concepts: list[RelatedConcept] = Field(default_factory=list)
    why_this_matters: list[str]
    source_backed_facts: list[str] = Field(default_factory=list)
    limitation_note: str = ""
    quiz: list[QuizQuestion] = Field(default_factory=list)
    remember_this: list[str] = Field(default_factory=list)

    @field_validator("primary_concept_name")
    @classmethod
    def _required_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("required text field is empty")
        return cleaned

    @field_validator("what_happened", "primary_concept_explanation", "why_this_matters")
    @classmethod
    def _required_bullets(cls, value: list[str]) -> list[str]:
        cleaned = _clean_bullets(value)
        if not cleaned:
            raise ValueError("required bullet list is empty")
        return cleaned


class CachedExplanation(ExplanationDraft):
    document_id: int
    prompt_version: str
    source_url: str
    cached: bool = False


class ExplanationProvider(Protocol):
    def generate(self, item: ExplanationItem) -> ExplanationDraft:
        """Return a structured concept revision for one stored RBI excerpt."""


class ExplanationConfigError(RuntimeError):
    """Raised when the AI provider is not configured."""


class ExplanationProviderError(RuntimeError):
    """Raised when the AI provider call fails."""


def normalize_revision_draft(draft: ExplanationDraft) -> ExplanationDraft:
    """Clamp bullet lists, optional sections, and quiz size for a concise daily revision."""
    related = draft.related_concepts[:3]
    # Prefer concept teaching over excerpt fact lists; keep at most one short fact if present.
    facts = _clean_bullets(draft.source_backed_facts)[:1]
    takeaways = _clean_bullets(draft.remember_this)[:4]
    quiz: list[QuizQuestion] = []
    for question in draft.quiz[:3]:
        options = [option.strip() for option in question.options if option.strip()][:4]
        if len(options) < 2:
            continue
        index = question.correct_option_index
        if index >= len(options):
            index = 0
        quiz.append(
            QuizQuestion(
                question=question.question.strip(),
                options=options,
                correct_option_index=index,
                explanation=question.explanation.strip(),
            )
        )
    return draft.model_copy(
        update={
            "what_happened": _clean_bullets(draft.what_happened)[:5],
            "primary_concept_explanation": _clean_bullets(draft.primary_concept_explanation)[:5],
            "how_it_works": _clean_bullets(draft.how_it_works)[:5],
            "why_this_matters": _clean_bullets(draft.why_this_matters)[:5],
            "related_concepts": related,
            "source_backed_facts": facts,
            "limitation_note": draft.limitation_note.strip(),
            "quiz": quiz,
            "remember_this": takeaways,
        }
    )
