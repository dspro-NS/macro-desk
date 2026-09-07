from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from macro_desk.db.repository import DocumentRepository, connect, initialize
from macro_desk.domain.taxonomy import TAXONOMY_VALUES
from macro_desk.ingestion.pipeline import ingest_configured_feeds
from macro_desk.ingestion.sources import DOCUMENT_TYPE_VALUES

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str = "macro-desk"


class DocumentSummary(BaseModel):
    id: int
    title: str
    published_at: datetime
    source: str
    source_url: str
    document_type: str
    content_hash: str
    category: str
    classification_reason: str
    created_at: datetime
    clean_text: str


class DocumentListResponse(BaseModel):
    items: List[DocumentSummary]
    count: int


class IngestResponse(BaseModel):
    fetched: int
    inserted: int
    skipped: int
    failed: int
    errors: List[str] = Field(default_factory=list)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    category: Optional[str] = Query(default=None),
    document_type: Optional[str] = Query(default=None),
) -> DocumentListResponse:
    if category is not None and category not in TAXONOMY_VALUES:
        raise HTTPException(
            status_code=400,
            detail="Unknown category. Use one of: {}".format(", ".join(TAXONOMY_VALUES)),
        )
    if document_type is not None and document_type not in DOCUMENT_TYPE_VALUES:
        raise HTTPException(
            status_code=400,
            detail="Unknown document_type. Use one of: {}".format(", ".join(DOCUMENT_TYPE_VALUES)),
        )
    settings = request.app.state.settings
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        items = DocumentRepository(connection).list_newest(
            limit=limit,
            category=category,
            document_type=document_type,
        )
    finally:
        connection.close()
    return DocumentListResponse(
        count=len(items),
        items=[
            DocumentSummary(
                id=item.id,
                title=item.title,
                published_at=item.published_at,
                source=item.source,
                source_url=item.source_url,
                document_type=item.document_type,
                content_hash=item.content_hash,
                category=item.category,
                classification_reason=item.classification_reason,
                created_at=item.created_at,
                clean_text=item.clean_text,
            )
            for item in items
        ],
    )


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: Request) -> IngestResponse:
    settings = request.app.state.settings
    connection = connect(settings.database_path)
    try:
        initialize(connection)
        result = ingest_configured_feeds(settings, DocumentRepository(connection))
    finally:
        connection.close()
    return IngestResponse(
        fetched=result.fetched,
        inserted=result.inserted,
        skipped=result.skipped,
        failed=result.failed,
        errors=result.errors,
    )
