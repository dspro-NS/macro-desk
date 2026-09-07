from __future__ import annotations

from macro_desk.domain.classification import ClassificationResult, classify_document
from macro_desk.domain.hashing import compute_content_hash, normalize_whitespace
from macro_desk.domain.models import Document, NewDocument
from macro_desk.domain.taxonomy import Category
from macro_desk.domain.text import html_to_text

__all__ = [
    "Category",
    "ClassificationResult",
    "Document",
    "NewDocument",
    "classify_document",
    "compute_content_hash",
    "html_to_text",
    "normalize_whitespace",
]
