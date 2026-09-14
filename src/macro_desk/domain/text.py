from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import List, Optional, Tuple

# Tags whose contents should not appear in plain-text product fields.
# Footnote markers like <sup>1</sup> are dropped entirely for titles/excerpts.
_SKIP_CONTENT_TAGS = frozenset({"script", "style", "sup", "sub"})
_BLOCK_TAGS = frozenset({"br", "p", "div", "tr", "li", "h1", "h2", "h3", "table"})
_TRAILING_TITLE_SEPARATOR = re.compile(r"[\s\-\u2013\u2014]+$")


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag in _SKIP_CONTENT_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth == 0 and tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_CONTENT_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth == 0 and tag in {"p", "div", "tr", "li", "table"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._chunks.append(data)

    def text(self) -> str:
        joined = unescape("".join(self._chunks))
        lines = [" ".join(line.split()) for line in joined.splitlines()]
        return "\n".join(line for line in lines if line).strip()


def html_to_text(raw_html: str) -> str:
    """Convert HTML (or HTML-tinged plain text) into normalized plain text."""
    parser = _HTMLTextExtractor()
    parser.feed(raw_html or "")
    parser.close()
    return parser.text()


def sanitize_plain_text(value: str) -> str:
    """Normalize a title or excerpt so HTML markup cannot leak into the UI."""
    return html_to_text(value or "")


def polish_display_title(value: str) -> str:
    """Sanitize a title for display and drop dangling trailing separators.

    RBI titles often end with a leftover `` -`` after a truncated subtitle.
    This is a presentation polish only; stored titles are unchanged.
    """
    text = sanitize_plain_text(value)
    return _TRAILING_TITLE_SEPARATOR.sub("", text).strip()
