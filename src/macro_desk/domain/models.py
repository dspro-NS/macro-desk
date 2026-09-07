from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Persisted RBI document record."""

    title: str
    published_at: datetime
    source: str
    source_url: str
    document_type: str
    raw_text: str
    clean_text: str
    content_hash: str
    category: str
    classification_reason: str
    importance: str
    importance_reason: str
    created_at: datetime
    id: Optional[int] = None


class NewDocument(BaseModel):
    """Fields required to persist a document."""

    title: str = Field(min_length=1)
    published_at: datetime
    source: str = Field(min_length=1)
    source_url: str
    document_type: str = Field(min_length=1)
    raw_text: str
    clean_text: str
    content_hash: str = Field(min_length=1)
    category: str = Field(min_length=1)
    classification_reason: str = Field(min_length=1)
    importance: str = Field(min_length=1)
    importance_reason: str = Field(min_length=1)


class IngestRun(BaseModel):
    """One completed ingestion of the configured official feeds."""

    started_at: datetime
    finished_at: datetime
    fetched: int
    inserted: int
    skipped: int
    failed: int
    errors: list[str] = Field(default_factory=list)
    id: Optional[int] = None
