from __future__ import annotations

from macro_desk.domain.text import html_to_text, polish_display_title, sanitize_plain_text


def test_sanitize_plain_text_strips_footnote_superscript() -> None:
    raw = "Getting ready for the next Decade<sup>1</sup> - Keynote"
    assert sanitize_plain_text(raw) == "Getting ready for the next Decade - Keynote"


def test_sanitize_plain_text_drops_common_html_tags_without_losing_words() -> None:
    raw = "<p>India's <strong>Foreign Exchange</strong> Markets<br>Getting ready</p>"
    cleaned = sanitize_plain_text(raw)
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "India's Foreign Exchange Markets" in cleaned
    assert "Getting ready" in cleaned


def test_sanitize_plain_text_skips_sup_and_sub_content() -> None:
    assert sanitize_plain_text("Policy<sup>2</sup> update") == "Policy update"
    # Subscript marker content is dropped (preferred for titles/metadata).
    assert sanitize_plain_text("H<sub>2</sub>O note") == "HO note"


def test_html_to_text_removes_em_and_nested_markup() -> None:
    cleaned = html_to_text("A <em>short</em> <b>note</b> with <a href='x'>link</a>.")
    assert cleaned == "A short note with link."


def test_polish_display_title_strips_trailing_hyphen() -> None:
    assert (
        polish_display_title("August 19, 2026 -")
        == "August 19, 2026"
    )
    assert (
        polish_display_title("Getting ready for the next Decade<sup>1</sup> - Keynote -")
        == "Getting ready for the next Decade - Keynote"
    )
    assert polish_display_title("Clean title") == "Clean title"


def test_sanitize_is_idempotent_on_plain_text() -> None:
    title = "Minutes of the Monetary Policy Committee Meeting"
    assert sanitize_plain_text(title) == title
    assert sanitize_plain_text(sanitize_plain_text(title)) == title
