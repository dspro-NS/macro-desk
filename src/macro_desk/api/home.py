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
.explain {
  margin: 0.65rem 0 0;
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 0.82rem;
  color: #5c5852;
}
.explain summary {
  cursor: pointer;
  list-style: none;
  color: #6b675f;
}
.explain summary::-webkit-details-marker { display: none; }
.explain summary::before {
  content: "";
  display: inline-block;
  width: 0.4rem;
  height: 0.4rem;
  margin-right: 0.4rem;
  border-right: 1px solid #8a857c;
  border-bottom: 1px solid #8a857c;
  transform: rotate(-45deg);
  vertical-align: 0.12rem;
}
.explain[open] summary::before { transform: rotate(45deg); }
.explain-body {
  margin: 0.55rem 0 0;
  padding: 0.7rem 0.8rem;
  background: #efeee9;
  border-radius: 3px;
  color: #3a3834;
}
.explain-body h4 {
  margin: 0.7rem 0 0.2rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #6b675f;
}
.explain-body h4:first-child { margin-top: 0; }
.explain-body p, .explain-body ul { margin: 0; }
.explain-body ul {
  padding-left: 1.1rem;
}
.explain-body .limitation {
  font-style: italic;
  color: #5c5852;
}
.explain-body .source-link {
  display: inline-block;
  margin-top: 0.55rem;
}
""".strip()

_HOME_JS = """
(function () {
  function messageForStatus(status) {
    if (status === 503) {
      return "Explanations are not configured on this desk.";
    }
    if (status === 502) {
      return "The explanation service failed. The original RBI source is still above.";
    }
    if (status === 404) {
      return "This item was not found.";
    }
    return "Could not load this explanation. Try again later.";
  }

  function addSection(body, heading, text) {
    var title = document.createElement("h4");
    title.textContent = heading;
    var paragraph = document.createElement("p");
    paragraph.textContent = text || "";
    body.appendChild(title);
    body.appendChild(paragraph);
  }

  function renderExplanation(body, data) {
    body.textContent = "";
    addSection(body, "What changed", data.what_changed);
    addSection(body, "Why it matters", data.why_it_matters);
    addSection(body, "Who should care", data.who_should_care);

    var evidenceTitle = document.createElement("h4");
    evidenceTitle.textContent = "Grounded in this RBI item";
    body.appendChild(evidenceTitle);
    var list = document.createElement("ul");
    (data.evidence_snippets || []).forEach(function (snippet) {
      var item = document.createElement("li");
      item.textContent = snippet;
      list.appendChild(item);
    });
    body.appendChild(list);

    if (data.limitation_note) {
      var limitationTitle = document.createElement("h4");
      limitationTitle.textContent = "Limitation";
      var limitation = document.createElement("p");
      limitation.className = "limitation";
      limitation.textContent = data.limitation_note;
      body.appendChild(limitationTitle);
      body.appendChild(limitation);
    }

    var link = document.createElement("a");
    link.className = "source-link";
    link.href = data.source_url;
    link.textContent = "Original RBI source";
    body.appendChild(link);
  }

  document.addEventListener("toggle", function (event) {
    var details = event.target;
    if (!details.classList || !details.classList.contains("explain") || !details.open) {
      return;
    }
    if (details.dataset.loaded === "1") {
      return;
    }
    var body = details.querySelector(".explain-body");
    var id = details.dataset.documentId;
    if (!body || !id) {
      return;
    }
    body.textContent = "Loading…";
    fetch("/documents/" + encodeURIComponent(id) + "/explanation", { method: "POST" })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, status: response.status, data: data };
        }).catch(function () {
          return { ok: response.ok, status: response.status, data: {} };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          body.textContent = result.data.detail || messageForStatus(result.status);
          return;
        }
        renderExplanation(body, result.data);
        details.dataset.loaded = "1";
      })
      .catch(function () {
        body.textContent = "Could not load this explanation. Try again later.";
      });
  }, true);
})();
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
        "  <script>" + _HOME_JS + "</script>\n"
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
    item_id = document.id if document.id is not None else ""
    explain = ""
    if document.id is not None:
        explain = (
            '<details class="explain" data-document-id="{item_id}">'
            "<summary>Explain why this matters</summary>"
            '<div class="explain-body">Drawn only from the stored RBI excerpt, not the full linked page.</div>'
            "</details>"
        ).format(item_id=item_id)
    return (
        "<li>"
        '<a class="title" href="{url}">{title}</a>'
        '<p class="meta">{source} · {category} · {importance} · {published}'
        ' · <a class="source-link" href="{url}">RBI source</a></p>'
        "{explain}"
        "</li>"
    ).format(
        url=url,
        title=title,
        source=source,
        category=category,
        importance=importance,
        published=published,
        explain=explain,
    )
