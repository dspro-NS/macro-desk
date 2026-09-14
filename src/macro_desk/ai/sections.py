from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from macro_desk.ai.contracts import ExplanationDraft, QuizQuestion, RelatedConcept

SectionKind = Literal["bullets", "concept", "connections", "quiz"]


class RevisionSection(BaseModel):
    """Presentation unit for the revision UI. Titles live here (content layer), not in CSS/JS."""

    id: str
    title: str
    kind: SectionKind
    bullets: list[str] = Field(default_factory=list)
    eyebrow: str = ""
    connections: list[RelatedConcept] = Field(default_factory=list)
    quiz: list[QuizQuestion] = Field(default_factory=list)


# Stable section catalogue. UI maps over returned sections; it does not hard-code RBI prose.
_SECTION_WHAT_HAPPENED = ("what_happened", "What happened?")
_SECTION_CONCEPT = ("concept", "What concept do I need to understand?")
_SECTION_HOW = ("how_it_works", "How does it work?")
_SECTION_CONNECTIONS = ("connections", "How does it connect to other concepts?")
_SECTION_WHY = ("why_it_matters", "Why does this update matter?")
_SECTION_RECALL = ("recall", "Can I recall it?")


def build_revision_sections(draft: ExplanationDraft) -> list[RevisionSection]:
    """Assemble ordered, optional revision sections from a stored draft.

    Empty optional content is omitted so the UI never renders blank accordions.
    Conceptual sections carry structured ``bullets``; the UI decides list presentation.
    """
    sections: list[RevisionSection] = []

    what = [item.strip() for item in draft.what_happened if item.strip()]
    if what:
        sid, title = _SECTION_WHAT_HAPPENED
        sections.append(RevisionSection(id=sid, title=title, kind="bullets", bullets=what))

    concept_name = draft.primary_concept_name.strip()
    concept_bullets = [item.strip() for item in draft.primary_concept_explanation if item.strip()]
    if concept_name and concept_bullets:
        sid, title = _SECTION_CONCEPT
        sections.append(
            RevisionSection(
                id=sid,
                title=title,
                kind="concept",
                eyebrow=concept_name,
                bullets=concept_bullets,
            )
        )

    how = [item.strip() for item in draft.how_it_works if item.strip()]
    if how:
        sid, title = _SECTION_HOW
        sections.append(RevisionSection(id=sid, title=title, kind="bullets", bullets=how))

    if draft.related_concepts:
        sid, title = _SECTION_CONNECTIONS
        sections.append(
            RevisionSection(
                id=sid,
                title=title,
                kind="connections",
                connections=list(draft.related_concepts),
            )
        )

    why = [item.strip() for item in draft.why_this_matters if item.strip()]
    if why:
        if draft.limitation_note.strip():
            why = why + [draft.limitation_note.strip()]
        sid, title = _SECTION_WHY
        sections.append(RevisionSection(id=sid, title=title, kind="bullets", bullets=why))

    if draft.quiz:
        sid, title = _SECTION_RECALL
        sections.append(
            RevisionSection(
                id=sid,
                title=title,
                kind="quiz",
                quiz=list(draft.quiz),
            )
        )

    return sections
