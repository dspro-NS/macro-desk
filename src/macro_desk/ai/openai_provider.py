from __future__ import annotations

import json
import logging

from openai import OpenAI

from macro_desk.ai.contracts import (
    EXPLANATION_JSON_SCHEMA,
    ExplanationDraft,
    ExplanationItem,
    ExplanationProviderError,
)

logger = logging.getLogger(__name__)

_INSTRUCTIONS = """You explain one stored RBI RSS excerpt for a personal India macro desk.

Rules:
- Use only the provided title, date, source, category, importance, URL, and excerpt.
- The excerpt is the stored RSS description, not necessarily the full linked RBI document.
- Do not invent facts, numbers, policy changes, or transmission effects that the excerpt does not state.
- If the excerpt is too thin to support an inference, say so in limitation_note and keep other fields cautious.
- evidence_snippets must be brief quotes or close paraphrases taken only from the excerpt (1 to 3 items).
- Do not use tools, web search, or outside knowledge presented as fact from this item.
"""


class OpenAIExplanationProvider:
    """OpenAI Responses API implementation. The only OpenAI-specific module."""

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = OpenAI(api_key=api_key, timeout=60.0)

    def generate(self, item: ExplanationItem) -> ExplanationDraft:
        try:
            response = self._client.responses.create(
                model=self._model,
                store=False,
                instructions=_INSTRUCTIONS,
                input=json.dumps(item.model_dump(), ensure_ascii=False),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "rbi_item_explanation",
                        "strict": True,
                        "schema": EXPLANATION_JSON_SCHEMA,
                    }
                },
            )
        except Exception as exc:
            logger.exception("OpenAI explanation request failed")
            raise ExplanationProviderError("The explanation service failed") from exc

        text = getattr(response, "output_text", None) or ""
        try:
            payload = json.loads(text)
            draft = ExplanationDraft.model_validate(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.exception("OpenAI explanation was not valid structured output")
            raise ExplanationProviderError("The explanation service returned invalid output") from exc
        snippets = [snippet.strip() for snippet in draft.evidence_snippets if snippet.strip()][:3]
        return draft.model_copy(update={"evidence_snippets": snippets})
