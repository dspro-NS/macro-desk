from __future__ import annotations

from datetime import datetime, timezone

from macro_desk.domain.importance import IMPORTANCE_VALUES, rank_importance
from macro_desk.domain.classification import classify_document
from macro_desk.domain.importance import rank_importance
from macro_desk.domain.models import NewDocument


def make_document(**overrides) -> NewDocument:
    payload = {
        "title": "RBI press release",
        "published_at": datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc),
        "source": "RBI Press Releases",
        "source_url": "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=1",
        "document_type": "press_release",
        "raw_text": "<p>Repo rate unchanged.</p>",
        "clean_text": "Repo rate unchanged.",
        "content_hash": "a" * 64,
    }
    payload.update(overrides)
    if "category" not in payload or "classification_reason" not in payload:
        result = classify_document(payload["title"], payload["clean_text"])
        payload.setdefault("category", result.category)
        payload.setdefault("classification_reason", result.reason)
    if "importance" not in payload or "importance_reason" not in payload:
        ranked = rank_importance(payload["title"], payload["clean_text"])
        payload.setdefault("importance", ranked.importance)
        payload.setdefault("importance_reason", ranked.reason)
    return NewDocument(**payload)
