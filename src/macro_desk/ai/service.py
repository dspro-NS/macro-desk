from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from macro_desk.ai.contracts import (
    PROMPT_VERSION,
    CachedExplanation,
    ExplanationConfigError,
    ExplanationItem,
    ExplanationProvider,
)
from macro_desk.ai.openai_provider import OpenAIExplanationProvider
from macro_desk.config import Settings
from macro_desk.db.repository import DocumentRepository
from macro_desk.domain.models import Document


def build_explanation_provider(settings: Settings) -> Optional[ExplanationProvider]:
    key = (settings.openai_api_key or "").strip()
    if not key:
        return None
    return OpenAIExplanationProvider(api_key=key, model=settings.openai_model)


def item_from_document(document: Document) -> ExplanationItem:
    return ExplanationItem(
        title=document.title,
        published_at=document.published_at.date().isoformat(),
        source=document.source,
        category=document.category,
        importance=document.importance,
        source_url=document.source_url,
        clean_text=document.clean_text,
    )


def explain_document(
    document: Document,
    repository: DocumentRepository,
    provider: Optional[ExplanationProvider],
    now: Optional[datetime] = None,
) -> CachedExplanation:
    if document.id is None:
        raise ValueError("Document must be persisted before it can be explained")
    cached = repository.get_explanation(document.id, PROMPT_VERSION)
    if cached is not None:
        return cached.model_copy(update={"cached": True})
    if provider is None:
        raise ExplanationConfigError("Explanations are not configured")
    draft = provider.generate(item_from_document(document))
    created = now or datetime.now(timezone.utc)
    stored = repository.save_explanation(
        document_id=document.id,
        prompt_version=PROMPT_VERSION,
        source_url=document.source_url,
        draft=draft,
        created_at=created,
    )
    return stored.model_copy(update={"cached": False})
