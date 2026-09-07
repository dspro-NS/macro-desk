from __future__ import annotations

import hashlib


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def compute_content_hash(title: str, clean_text: str) -> str:
    """Return a stable SHA-256 hash of document content.

    The hash is independent of source URL so the same text published at a
    different URL is still treated as a duplicate.
    """
    canonical = "{}\n{}".format(normalize_whitespace(title), clean_text.strip())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
