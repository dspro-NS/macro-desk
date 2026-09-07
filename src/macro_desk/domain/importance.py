from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

IMPORTANCE_HIGH = "high"
IMPORTANCE_MEDIUM = "medium"
IMPORTANCE_LOW = "low"
IMPORTANCE_VALUES = (IMPORTANCE_HIGH, IMPORTANCE_MEDIUM, IMPORTANCE_LOW)

_LOW_TITLE_PATTERNS = (
    "appointment of",
    "assumes office",
    "demits office",
    "public holiday",
    "bank holiday",
    "tender notice",
    "recruitment",
    "obituary",
    "condolence",
    "outreach programme",
    "result of variable rate",
    "result of the auction",
    "government securities auction",
    "treasury bill auction",
)

_HIGH_TERMS = (
    "monetary policy committee",
    "monetary policy statement",
    "minutes of the monetary policy",
    "statement on developmental and regulatory",
    "financial stability report",
    "master direction",
    "policy repo rate",
    "cash reserve ratio",
    "review of cash reserve",
)

_MEDIUM_TERMS = (
    "deputy governor",
    "executive director",
    "master circular",
    "know your customer",
    "unified payments interface",
    "payment system",
    "bank licence",
    "bank license",
    "urban co-operative",
    "consumer price index",
    "gross domestic product",
    "circular",
    "notification",
    "guidelines",
    "kyc",
    "nbfc",
    "upi",
    "cpi",
    "gdp",
)


@dataclass(frozen=True)
class ImportanceResult:
    importance: str
    reason: str


class DocumentImportanceRanker(Protocol):
    """Replaceable ranker. An LLM implementation can use this same contract."""

    def rank(self, title: str, clean_text: str) -> ImportanceResult:
        ...


class KeywordImportanceRanker:
    """Transparent high/medium/low rubric for Milestone documents."""

    def rank(self, title: str, clean_text: str) -> ImportanceResult:
        title_norm = _normalize(title)
        combined = "{} {}".format(title_norm, _normalize(clean_text)).strip()

        low_hits = [pattern for pattern in _LOW_TITLE_PATTERNS if pattern in title_norm]
        if low_hits:
            return ImportanceResult(
                importance=IMPORTANCE_LOW,
                reason="Administrative or operational title ({})".format(", ".join(low_hits)),
            )

        high_hits = [term for term in _HIGH_TERMS if _contains(combined, term)]
        if not high_hits and _governor_speech(title_norm, combined):
            high_hits = ["governor speech"]
        if high_hits:
            return ImportanceResult(
                importance=IMPORTANCE_HIGH,
                reason="High-importance terms: {}".format(", ".join(high_hits)),
            )

        medium_hits = [term for term in _MEDIUM_TERMS if _contains(combined, term)]
        if medium_hits:
            return ImportanceResult(
                importance=IMPORTANCE_MEDIUM,
                reason="Medium-importance terms: {}".format(", ".join(medium_hits)),
            )

        return ImportanceResult(
            importance=IMPORTANCE_LOW,
            reason="No high or medium importance terms in title or clean text",
        )


DEFAULT_RANKER: DocumentImportanceRanker = KeywordImportanceRanker()


def rank_importance(
    title: str,
    clean_text: str,
    ranker: DocumentImportanceRanker | None = None,
) -> ImportanceResult:
    active = ranker or DEFAULT_RANKER
    return active.rank(title, clean_text)


def _governor_speech(title_norm: str, combined: str) -> bool:
    if "deputy governor" in combined:
        return False
    if "governor" not in title_norm:
        return False
    return "speech" in combined or "keynote" in combined or "address" in combined


def _normalize(value: str) -> str:
    return " ".join((value or "").lower().split())


def _contains(haystack: str, phrase: str) -> bool:
    if not phrase:
        return False
    if re.search(r"\w", phrase) and " " not in phrase:
        return re.search(r"\b{}\b".format(re.escape(phrase)), haystack) is not None
    return phrase in haystack
