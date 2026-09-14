from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


PROMPT_VERSION = "explain-v1"

EXPLANATION_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "what_changed": {"type": "string"},
        "why_it_matters": {"type": "string"},
        "who_should_care": {"type": "string"},
        "evidence_snippets": {
            "type": "array",
            "items": {"type": "string"},
        },
        "limitation_note": {"type": "string"},
    },
    "required": [
        "what_changed",
        "why_it_matters",
        "who_should_care",
        "evidence_snippets",
        "limitation_note",
    ],
    "additionalProperties": False,
}


class ExplanationItem(BaseModel):
    """Fields sent to the model. Nothing else from the stored document."""

    title: str
    published_at: str
    source: str
    category: str
    importance: str
    source_url: str
    clean_text: str


class ExplanationDraft(BaseModel):
    what_changed: str
    why_it_matters: str
    who_should_care: str
    evidence_snippets: list[str] = Field(default_factory=list)
    limitation_note: str = ""


class CachedExplanation(ExplanationDraft):
    document_id: int
    prompt_version: str
    source_url: str
    cached: bool = False


class ExplanationProvider(Protocol):
    def generate(self, item: ExplanationItem) -> ExplanationDraft:
        """Return a structured explanation for one stored RBI excerpt."""


class ExplanationConfigError(RuntimeError):
    """Raised when the AI provider is not configured."""


class ExplanationProviderError(RuntimeError):
    """Raised when the AI provider call fails."""
