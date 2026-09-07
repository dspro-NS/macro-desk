from __future__ import annotations

from datetime import datetime, timezone

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
    return NewDocument(**payload)
