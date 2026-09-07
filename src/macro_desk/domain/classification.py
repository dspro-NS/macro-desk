from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from macro_desk.domain.taxonomy import TIE_BREAK_ORDER, Category

# Administrative titles that should not be stretched into a policy category.
_OTHER_TITLE_PATTERNS = (
    "appointment of",
    "assumes office",
    "demits office",
    "public holiday",
    "bank holiday",
    "tender notice",
    "recruitment",
    "obituary",
    "condolence",
)


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    reason: str


class DocumentClassifier(Protocol):
    """Replaceable classifier. An LLM implementation can use this same contract."""

    def classify(self, title: str, clean_text: str) -> ClassificationResult:
        ...


@dataclass(frozen=True)
class _Term:
    phrase: str
    weight: int = 1


def _terms(*phrases: str, weight: int = 1) -> tuple[_Term, ...]:
    return tuple(_Term(phrase=phrase, weight=weight) for phrase in phrases)


_CATEGORY_TERMS: dict[Category, tuple[_Term, ...]] = {
    Category.MONETARY_POLICY: _terms(
        "monetary policy committee",
        "monetary policy statement",
        "minutes of the monetary policy",
        "statement on developmental and regulatory",
        "policy repo rate",
        "mpc meeting",
        "mpc minutes",
        "repo rate",
        "msf rate",
        "bank rate",
        "accommodation stance",
        "policy stance",
        "standing deposit facility rate",
        weight=2,
    )
    + _terms("monetary policy", "mpc"),
    Category.PAYMENTS: _terms(
        "unified payments interface",
        "prepaid payment instrument",
        "payment system operator",
        "digital payments",
        "payment systems",
        weight=2,
    )
    + _terms("upi", "neft", "rtgs", "imps", "ppi", "aeeps"),
    Category.FINANCIAL_STABILITY: _terms(
        "financial stability report",
        "systemic risk",
        "stress test",
        "too-big-to-fail",
        weight=2,
    )
    + _terms("financial stability", "macroprudential"),
    Category.FX_EXTERNAL: _terms(
        "foreign exchange reserves",
        "external commercial borrowing",
        "current account deficit",
        "foreign portfolio investment",
        "liberalised remittance",
        weight=2,
    )
    + _terms(
        "exchange rate",
        "forex",
        "usd/inr",
        "fpi",
        "ecb",
        "lrs",
        "rupee",
        "external sector",
    ),
    Category.INFLATION: _terms(
        "consumer price index",
        "wholesale price index",
        "inflation target",
        weight=2,
    )
    + _terms("inflation", "cpi", "wpi"),
    Category.GROWTH: _terms(
        "gross domestic product",
        "index of industrial production",
        "industrial production",
        weight=2,
    )
    + _terms("gdp", "iip", "gva", "economic growth"),
    Category.LIQUIDITY: _terms(
        "variable rate reverse repo",
        "variable rate repo",
        "open market operation",
        "government securities auction",
        "liquidity adjustment facility",
        "cash reserve ratio",
        "statutory liquidity ratio",
        "durable liquidity",
        weight=2,
    )
    + _terms(
        "vrrr",
        "vrr",
        "omo",
        "crr",
        "slr",
        "laf",
        "sdf auction",
        "repo auction",
        "surplus liquidity",
        "liquidity",
        "g-sec",
        "t-bill",
        "treasury bill",
    ),
    Category.REGULATION: _terms(
        "master direction",
        "master circular",
        "prudential regulation",
        "know your customer",
        "scale-based regulation",
        weight=2,
    )
    + _terms("circular", "notification", "guidelines", "kyc", "aml", "nbfc"),
    Category.BANKING: _terms(
        "scheduled commercial bank",
        "urban co-operative bank",
        "co-operative bank",
        "non-performing asset",
        "priority sector lending",
        "bank licence",
        "bank license",
        weight=2,
    )
    + _terms("npa", "gnpa", "psl", "credit growth", "commercial bank"),
}


class KeywordRuleClassifier:
    """Deterministic title/body keyword classifier for Milestone 2."""

    def classify(self, title: str, clean_text: str) -> ClassificationResult:
        title_norm = _normalize(title)
        body_norm = _normalize(clean_text)
        combined = "{} {}".format(title_norm, body_norm).strip()

        other_hits = [pattern for pattern in _OTHER_TITLE_PATTERNS if pattern in title_norm]
        if other_hits:
            return ClassificationResult(
                category=Category.OTHER.value,
                reason="Title looks administrative ({})".format(", ".join(other_hits)),
            )

        scores: dict[Category, int] = {}
        matched: dict[Category, list[str]] = {}
        title_matched: dict[Category, list[str]] = {}
        for category, terms in _CATEGORY_TERMS.items():
            for term in terms:
                if not _contains(combined, term.phrase):
                    continue
                scores[category] = scores.get(category, 0) + term.weight
                matched.setdefault(category, [])
                if term.phrase not in matched[category]:
                    matched[category].append(term.phrase)
                if _contains(title_norm, term.phrase):
                    scores[category] += term.weight
                    title_matched.setdefault(category, [])
                    if term.phrase not in title_matched[category]:
                        title_matched[category].append(term.phrase)

        if not scores:
            return ClassificationResult(
                category=Category.OTHER.value,
                reason="No taxonomy keywords in title or clean text",
            )

        best_score = max(scores.values())
        winners = [category for category in TIE_BREAK_ORDER if scores.get(category) == best_score]
        chosen = winners[0]
        phrases = matched[chosen]
        reason = "Matched {} terms: {}".format(chosen.value, ", ".join(phrases))
        title_phrases = title_matched.get(chosen) or []
        if title_phrases:
            reason += " (title: {})".format(", ".join(title_phrases))
        return ClassificationResult(category=chosen.value, reason=reason)


DEFAULT_CLASSIFIER: DocumentClassifier = KeywordRuleClassifier()


def classify_document(
    title: str,
    clean_text: str,
    classifier: DocumentClassifier | None = None,
) -> ClassificationResult:
    active = classifier or DEFAULT_CLASSIFIER
    return active.classify(title, clean_text)


def _normalize(value: str) -> str:
    return " ".join((value or "").lower().split())


def _contains(haystack: str, phrase: str) -> bool:
    if not phrase:
        return False
    if re.search(r"\w", phrase) and " " not in phrase and "/" not in phrase:
        return re.search(r"\b{}\b".format(re.escape(phrase)), haystack) is not None
    return phrase in haystack
