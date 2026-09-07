from __future__ import annotations

from html import escape
from typing import Sequence

from macro_desk.domain.models import Document

_HOME_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #f7f6f2;
  color: #1c1b19;
  font-family: Georgia, "Times New Roman", Times, serif;
  line-height: 1.45;
}
main {
  max-width: 40rem;
  margin: 0 auto;
  padding: 2.5rem 1.25rem 4rem;
}
h1 {
  margin: 0 0 0.25rem;
  font-size: 1.6rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.lede {
  margin: 0 0 2rem;
  color: #5c5852;
  font-size: 0.95rem;
}
.updates {
  list-style: none;
  margin: 0;
  padding: 0;
}
.updates li {
  padding: 1.1rem 0;
  border-top: 1px solid #e4e0d8;
}
.updates li:last-child { border-bottom: 1px solid #e4e0d8; }
.title {
  display: inline-block;
  color: #1c1b19;
  text-decoration: none;
  font-size: 1.05rem;
}
.title:hover { text-decoration: underline; }
.meta {
  margin: 0.4rem 0 0;
  color: #5c5852;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.8rem;
  letter-spacing: 0.01em;
}
.source-link {
  color: #5c5852;
  text-underline-offset: 2px;
}
.empty {
  padding: 1.5rem 0;
  border-top: 1px solid #e4e0d8;
  color: #5c5852;
}
""".strip()


def render_home(documents: Sequence[Document], hours: int = 24) -> str:
    if documents:
        items = "\n".join(_render_item(document) for document in documents)
        body = '<ol class="updates">\n{}\n</ol>'.format(items)
    else:
        body = (
            '<p class="empty">Nothing new in the last {} hours.</p>'.format(hours)
        )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "  <title>Macro Desk</title>\n"
        "  <style>" + _HOME_CSS + "</style>\n"
        "</head>\n"
        "<body>\n"
        "  <main>\n"
        "    <h1>Macro Desk</h1>\n"
        '    <p class="lede">Latest updates first seen in the last '
        + str(hours)
        + " hours.</p>\n"
        "    " + body + "\n"
        "  </main>\n"
        "</body>\n"
        "</html>\n"
    )


def _render_item(document: Document) -> str:
    title = escape(document.title)
    source = escape(document.source)
    category = escape(document.category)
    importance = escape(document.importance)
    published = escape(document.published_at.date().isoformat())
    url = escape(document.source_url, quote=True)
    return (
        "<li>"
        '<a class="title" href="{url}">{title}</a>'
        '<p class="meta">{source} · {category} · {importance} · {published}'
        ' · <a class="source-link" href="{url}">RBI source</a></p>'
        "</li>"
    ).format(
        url=url,
        title=title,
        source=source,
        category=category,
        importance=importance,
        published=published,
    )
