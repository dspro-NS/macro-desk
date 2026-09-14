from __future__ import annotations

from html import escape
from typing import Sequence

from macro_desk.domain.models import Document
from macro_desk.domain.text import polish_display_title, sanitize_plain_text

_HOME_CSS = """
:root {
  color-scheme: light;
  --ink: #1a2744;
  --ink-soft: #5a6a82;
  --page: #f7f3eb;
  --paper: #fffaf3;
  --paper-edge: #ebe4d8;
  --lavender: #b8a8c9;
  --lavender-soft: rgba(184, 168, 201, 0.18);
  --blush: #d4a8b0;
  --blush-soft: rgba(212, 168, 176, 0.18);
  --powder: #a8bfd0;
  --powder-soft: rgba(168, 191, 208, 0.18);
  --sage: #9bb3a0;
  --sage-soft: rgba(155, 179, 160, 0.18);
  --peach: #d8b49a;
  --peach-soft: rgba(216, 180, 154, 0.18);
  --success-soft: rgba(155, 179, 160, 0.28);
  --danger-soft: rgba(212, 168, 176, 0.28);
  --border: rgba(26, 39, 68, 0.08);
  --font-display: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  --font-ui: "Avenir Next", "Segoe UI", ui-sans-serif, system-ui, sans-serif;
  --radius: 14px;
  --shadow-notebook: 0 18px 48px rgba(26, 39, 68, 0.07), 0 2px 0 rgba(255, 255, 255, 0.55) inset;
  --color-bg: var(--page);
  --color-text: var(--ink);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  font-family: var(--font-display);
  line-height: 1.55;
  background: var(--page);
  position: relative;
  overflow-x: hidden;
}

body::before,
body::after {
  content: "";
  position: fixed;
  inset: auto;
  pointer-events: none;
  z-index: 0;
  filter: blur(48px);
  opacity: 0.45;
}

body::before {
  top: -12%;
  left: -8%;
  width: 55vw;
  height: 42vw;
  border-radius: 55% 45% 60% 40%;
  background:
    radial-gradient(circle at 30% 40%, rgba(184, 168, 201, 0.35), transparent 62%),
    radial-gradient(circle at 70% 60%, rgba(168, 191, 208, 0.28), transparent 58%);
}

body::after {
  right: -10%;
  bottom: -8%;
  width: 50vw;
  height: 40vw;
  border-radius: 40% 60% 45% 55%;
  background:
    radial-gradient(circle at 40% 35%, rgba(212, 168, 176, 0.28), transparent 60%),
    radial-gradient(circle at 65% 70%, rgba(155, 179, 160, 0.22), transparent 55%),
    radial-gradient(circle at 20% 80%, rgba(216, 180, 154, 0.2), transparent 50%);
}

.app {
  position: relative;
  z-index: 1;
  max-width: 72rem;
  margin: 0 auto;
  padding: 2.75rem 2rem 4.5rem;
}

.view[hidden] { display: none !important; }

.hero {
  max-width: 38rem;
  margin: 0 0 2.75rem;
}

.brand {
  margin: 0 0 0.55rem;
  font-family: var(--font-display);
  font-size: clamp(2rem, 3.4vw, 2.55rem);
  font-weight: 650;
  letter-spacing: -0.03em;
  color: var(--ink);
}

.greeting {
  margin: 0;
  font-family: var(--font-ui);
  font-size: 1.02rem;
  color: var(--ink-soft);
  letter-spacing: 0.01em;
}

.list-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem 1.25rem;
  margin: 0 0 1.15rem;
  max-width: 46rem;
}

.list-label {
  margin: 0;
  font-family: var(--font-ui);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink);
}

.list-sub {
  margin: 0;
  font-family: var(--font-ui);
  font-size: 0.82rem;
  color: var(--ink-soft);
}

.home-layout {
  display: grid;
  grid-template-columns: minmax(0, 46rem) minmax(0, 1fr);
  gap: 2.5rem;
  align-items: start;
}

.brand-side {
  position: sticky;
  top: 2.5rem;
  padding: 1.5rem 0.25rem;
  font-family: var(--font-ui);
  color: var(--ink-soft);
  opacity: 0.72;
}

.brand-side p {
  margin: 0;
  max-width: 14rem;
  font-size: 0.84rem;
  line-height: 1.55;
}

.brand-mark {
  display: block;
  width: 2.25rem;
  height: 0.28rem;
  margin-bottom: 1rem;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--lavender), var(--powder), var(--sage));
  opacity: 0.7;
}

.updates {
  list-style: none;
  margin: 0;
  padding: 0;
  max-width: 46rem;
}

.update-card {
  position: relative;
  margin: 0 0 0.85rem;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--paper) 88%, white);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.65) inset;
  transition: border-color 140ms ease, background 140ms ease, box-shadow 140ms ease, transform 140ms ease;
}

.update-card:hover {
  border-color: color-mix(in srgb, var(--lavender) 35%, var(--border));
  background: var(--paper);
  box-shadow: 0 8px 22px rgba(26, 39, 68, 0.05);
  transform: translateY(-1px);
}

.update-open {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
  padding: 1.15rem 1.25rem 1.05rem;
}

.update-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0 0 0.55rem;
}

.pill {
  display: inline-block;
  padding: 0.14rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.55);
  font-family: var(--font-ui);
  font-size: 0.68rem;
  letter-spacing: 0.03em;
  color: var(--ink-soft);
}

.pill-type { background: var(--powder-soft); border-color: transparent; color: #3d5670; }
.pill-category { background: var(--lavender-soft); border-color: transparent; color: #5a4e6e; }
.pill-importance-high { background: var(--peach-soft); border-color: transparent; color: #7a5640; }
.pill-importance-medium { background: var(--sage-soft); border-color: transparent; color: #45604c; }
.pill-importance-low { background: rgba(255, 255, 255, 0.55); }

.update-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.18rem;
  font-weight: 650;
  letter-spacing: -0.015em;
  line-height: 1.35;
  color: var(--ink);
  transition: color 140ms ease;
}

.update-card:hover .update-title {
  color: color-mix(in srgb, var(--ink) 82%, var(--lavender));
}

.update-support {
  margin: 0.45rem 0 0;
  font-family: var(--font-ui);
  font-size: 0.86rem;
  color: var(--ink-soft);
  line-height: 1.45;
  max-width: 40rem;
}

.update-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 0.85rem;
  font-family: var(--font-ui);
  font-size: 0.78rem;
  color: var(--ink-soft);
}

.update-open-hint {
  opacity: 0.35;
  transition: transform 140ms ease, opacity 140ms ease;
  color: color-mix(in srgb, var(--ink) 70%, var(--lavender));
}

.update-card:hover .update-open-hint {
  opacity: 0.75;
  transform: translateX(2px);
}

.source-link {
  color: color-mix(in srgb, var(--ink) 65%, var(--powder));
  text-underline-offset: 2px;
  font-family: var(--font-ui);
  font-size: 0.78rem;
}

.update-source {
  display: inline-block;
  margin: 0 1.25rem 1rem;
}

.empty {
  margin: 0;
  padding: 1.5rem 0;
  border-top: 1px solid var(--border);
  color: var(--ink-soft);
  font-family: var(--font-ui);
  max-width: 46rem;
}

.notebook-top {
  margin: 0 0 1.35rem;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0 0 1.25rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-soft);
  font-family: var(--font-ui);
  font-size: 0.82rem;
  cursor: pointer;
}

.back-btn:hover { color: var(--ink); }

.article-header {
  max-width: 52rem;
}

.article-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0 0 0.75rem;
}

.article-title {
  margin: 0 0 0.55rem;
  font-family: var(--font-display);
  font-size: clamp(1.45rem, 2.4vw, 1.85rem);
  font-weight: 650;
  letter-spacing: -0.02em;
  line-height: 1.28;
  color: var(--ink);
}

.article-sub {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  align-items: center;
  margin: 0;
  font-family: var(--font-ui);
  font-size: 0.82rem;
  color: var(--ink-soft);
}

.notebook {
  display: grid;
  grid-template-columns: minmax(15rem, 0.92fr) 2px minmax(0, 1.35fr);
  align-items: stretch;
  min-height: 28rem;
  margin-top: 0.35rem;
  border-radius: 18px;
  background: transparent;
  filter: drop-shadow(0 18px 40px rgba(26, 39, 68, 0.06));
  position: relative;
}

.nb-page {
  background: var(--paper);
  border: 1px solid color-mix(in srgb, var(--ink) 14%, var(--paper-edge));
  min-height: 28rem;
  position: relative;
  z-index: 1;
}

.nb-left {
  border-radius: 18px 0 0 18px;
  border-right: 0;
  padding: 1.35rem 0.85rem 1.35rem 1.1rem;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.35) inset,
    inset -5px 0 8px -6px rgba(140, 120, 95, 0.07);
}

.nb-right {
  border-radius: 0 18px 18px 0;
  border-left: 0;
  padding: 1.55rem 1.55rem 1.65rem;
  display: flex;
  flex-direction: column;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.35) inset,
    inset 5px 0 8px -6px rgba(140, 120, 95, 0.07);
}

/* Barely-visible paper crease — quiet fold, not a spine */
.nb-gutter {
  align-self: stretch;
  min-height: 100%;
  pointer-events: none;
  background: color-mix(in srgb, var(--paper) 72%, #d2c6b4);
}

.section-nav {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.section-nav button {
  display: grid;
  grid-template-columns: 2rem 1fr;
  gap: 0.65rem;
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: var(--ink);
  font: inherit;
  cursor: pointer;
  padding: 0.7rem 0.65rem;
  transition: background 140ms ease, border-color 140ms ease;
}

.section-nav button:hover {
  background: rgba(255, 255, 255, 0.55);
}

.section-nav button.is-active {
  border-color: transparent;
}

.section-nav button[data-tone="lavender"].is-active { background: var(--lavender-soft); }
.section-nav button[data-tone="blush"].is-active { background: var(--blush-soft); }
.section-nav button[data-tone="powder"].is-active { background: var(--powder-soft); }
.section-nav button[data-tone="sage"].is-active { background: var(--sage-soft); }
.section-nav button[data-tone="peach"].is-active { background: var(--peach-soft); }

.sec-num {
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-ui);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid transparent;
}

button[data-tone="lavender"] .sec-num { background: var(--lavender-soft); color: #5a4e6e; }
button[data-tone="blush"] .sec-num { background: var(--blush-soft); color: #6e4a52; }
button[data-tone="powder"] .sec-num { background: var(--powder-soft); color: #3d5670; }
button[data-tone="sage"] .sec-num { background: var(--sage-soft); color: #45604c; }
button[data-tone="peach"] .sec-num { background: var(--peach-soft); color: #7a5640; }

.sec-copy { min-width: 0; }
.sec-title {
  display: block;
  font-family: var(--font-ui);
  font-size: 0.84rem;
  font-weight: 650;
  letter-spacing: 0.005em;
  color: var(--ink);
  margin-bottom: 0.12rem;
}
.sec-blurb {
  display: block;
  font-family: var(--font-ui);
  font-size: 0.72rem;
  color: var(--ink-soft);
  line-height: 1.35;
}

.rev-label {
  margin: 0 0 0.35rem;
  font-family: var(--font-ui);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: var(--ink-soft);
}

.rev-heading {
  margin: 0 0 1.1rem;
  font-family: var(--font-display);
  font-size: 1.28rem;
  font-weight: 650;
  letter-spacing: -0.015em;
  color: var(--ink);
  line-height: 1.3;
}

.rev-panel {
  flex: 1 1 auto;
  font-family: var(--font-display);
  font-size: 1rem;
  line-height: 1.6;
  color: var(--ink);
}

.rev-eyebrow {
  margin: 0 0 0.7rem;
  font-family: var(--font-ui);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--blush) 70%, var(--ink));
}

.rev-bullets {
  margin: 0;
  padding: 0 0 0 1.1rem;
  list-style: disc;
}

.rev-bullets li {
  margin: 0 0 0.7rem;
  padding-left: 0.2rem;
}

.rev-bullets li:last-child { margin-bottom: 0; }

.rev-connection strong {
  font-family: var(--font-ui);
  font-weight: 650;
  color: color-mix(in srgb, var(--ink) 85%, var(--powder));
}

.rev-empty {
  margin: 0;
  font-family: var(--font-ui);
  font-size: 0.9rem;
  color: var(--ink-soft);
}

.key-takeaway {
  margin-top: 1.35rem;
  padding: 0.85rem 0.95rem;
  border-radius: 12px;
  background: var(--lavender-soft);
  border: 1px solid transparent;
}

.key-takeaway-label {
  margin: 0 0 0.35rem;
  font-family: var(--font-ui);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-soft);
}

.key-takeaway p {
  margin: 0;
  font-family: var(--font-display);
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--ink);
}

.quiz-item {
  margin: 0 0 1rem;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid var(--border);
}

.quiz-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: 0;
}

.quiz-q {
  margin: 0 0 0.55rem;
  font-family: var(--font-ui);
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--ink);
}

.quiz-options {
  list-style: none;
  margin: 0;
  padding: 0;
}

.quiz-options li { margin: 0.3rem 0; }

.quiz-options button {
  display: block;
  width: 100%;
  text-align: left;
  font: inherit;
  font-family: var(--font-ui);
  font-size: 0.84rem;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.5rem 0.65rem;
  cursor: pointer;
  transition: border-color 120ms ease, background 120ms ease;
}

.quiz-options button:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--powder) 45%, var(--border));
  background: var(--powder-soft);
}

.quiz-options button:disabled { cursor: default; }

.quiz-options button.is-correct {
  border-color: color-mix(in srgb, var(--sage) 55%, var(--border));
  background: var(--success-soft);
}

.quiz-options button.is-wrong {
  border-color: color-mix(in srgb, var(--blush) 55%, var(--border));
  background: var(--danger-soft);
}

.quiz-feedback {
  margin: 0.5rem 0 0;
  font-family: var(--font-ui);
  font-size: 0.8rem;
  color: var(--ink-soft);
}

.revision-status {
  margin: 0;
  font-family: var(--font-ui);
  color: var(--ink-soft);
}

.revision-source {
  margin-top: 1rem;
  display: inline-block;
}

@media (max-width: 960px) {
  .home-layout { grid-template-columns: 1fr; }
  .brand-side { display: none; }
  .app { padding: 2rem 1.25rem 3.5rem; }
  .notebook {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
  .nb-gutter { display: none; }
  .nb-left,
  .nb-right {
    border-radius: 16px;
    border-color: color-mix(in srgb, var(--ink) 14%, var(--paper-edge));
    min-height: 0;
    box-shadow:
      0 0 0 1px rgba(255, 255, 255, 0.4) inset,
      0 1px 0 rgba(26, 39, 68, 0.03);
  }
  .nb-left {
    margin-bottom: 0;
    padding: 0.85rem;
  }
  .section-nav {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.35rem;
  }
  .section-nav button {
    grid-template-columns: 1.6rem 1fr;
    padding: 0.55rem;
  }
  .sec-blurb { display: none; }
}

@media (max-width: 640px) {
  .section-nav { grid-template-columns: 1fr; }
  .update-title { font-size: 1.05rem; }
  .brand { font-size: 1.75rem; }
}

@media (prefers-reduced-motion: reduce) {
  .update-card,
  .update-open-hint,
  .update-title,
  .section-nav button,
  .quiz-options button {
    transition: none;
  }
}
""".strip()

_HOME_JS = """
(function () {
  var SECTION_CATALOGUE = [
    {
      id: "what_happened",
      num: "01",
      title: "What happened?",
      blurb: "A quick summary of today's update.",
      tone: "lavender",
      heading: "A quick summary of today's update."
    },
    {
      id: "concept",
      num: "02",
      title: "What concept do I need to understand?",
      blurb: "The key idea behind the update.",
      tone: "blush",
      heading: "The key idea behind the update."
    },
    {
      id: "how_it_works",
      num: "03",
      title: "How does it work?",
      blurb: "The mechanism, step by step.",
      tone: "powder",
      heading: "The mechanism, step by step."
    },
    {
      id: "connections",
      num: "04",
      title: "How does it connect to other concepts?",
      blurb: "Where this sits in the larger system.",
      tone: "sage",
      heading: "Where this sits in the larger system."
    },
    {
      id: "why_it_matters",
      num: "05",
      title: "Why does this update matter?",
      blurb: "What changes in the real world.",
      tone: "peach",
      heading: "What changes in the real world."
    },
    {
      id: "recall",
      num: "06",
      title: "Can I recall it?",
      blurb: "A short knowledge check.",
      tone: "lavender",
      heading: "A short knowledge check."
    }
  ];

  function messageForStatus(status) {
    if (status === 503) {
      return "Concept revision is not configured on this desk.";
    }
    if (status === 502) {
      return "Concept revision failed. The original RBI source is still available.";
    }
    if (status === 404) {
      return "This item was not found.";
    }
    return "Could not load this revision. Try again later.";
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text != null && text !== "") {
      node.textContent = text;
    }
    return node;
  }

  function listView() { return document.getElementById("view-list"); }
  function notebookView() { return document.getElementById("view-notebook"); }

  function showList() {
    var list = listView();
    var notebook = notebookView();
    if (list) { list.hidden = false; }
    if (notebook) { notebook.hidden = true; }
    window.scrollTo(0, 0);
  }

  function showNotebook() {
    var list = listView();
    var notebook = notebookView();
    if (list) { list.hidden = true; }
    if (notebook) { notebook.hidden = false; }
    window.scrollTo(0, 0);
  }

  function renderBullets(panel, section) {
    if (section.eyebrow) {
      panel.appendChild(el("p", "rev-eyebrow", section.eyebrow));
    }
    var bullets = section.bullets || [];
    if (!bullets.length) {
      return;
    }
    var list = el("ul", "rev-bullets");
    bullets.forEach(function (item) {
      list.appendChild(el("li", null, item));
    });
    panel.appendChild(list);
  }

  function renderConnections(panel, section) {
    var list = el("ul", "rev-bullets");
    (section.connections || []).forEach(function (related) {
      var li = document.createElement("li");
      li.className = "rev-connection";
      if (related.name) {
        li.appendChild(el("strong", null, related.name));
        li.appendChild(document.createTextNode(" — "));
      }
      var parts = [];
      if (related.explanation) { parts.push(related.explanation); }
      if (related.why_relevant) { parts.push(related.why_relevant); }
      li.appendChild(document.createTextNode(parts.join(" ")));
      list.appendChild(li);
    });
    panel.appendChild(list);
  }

  function renderQuiz(panel, section) {
    (section.quiz || []).forEach(function (item, index) {
      var block = el("div", "quiz-item");
      block.appendChild(el("p", "quiz-q", (index + 1) + ". " + item.question));
      var options = el("ul", "quiz-options");
      var feedback = el("p", "quiz-feedback");
      (item.options || []).forEach(function (label, optionIndex) {
        var li = document.createElement("li");
        var button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.addEventListener("click", function () {
          if (block.dataset.answered === "1") { return; }
          block.dataset.answered = "1";
          var buttons = options.querySelectorAll("button");
          buttons.forEach(function (btn) { btn.disabled = true; });
          var correct = Number(item.correct_option_index);
          if (optionIndex === correct) {
            button.classList.add("is-correct");
          } else {
            button.classList.add("is-wrong");
            if (buttons[correct]) { buttons[correct].classList.add("is-correct"); }
          }
          feedback.textContent = item.explanation || "";
        });
        li.appendChild(button);
        options.appendChild(li);
      });
      block.appendChild(options);
      block.appendChild(feedback);
      panel.appendChild(block);
    });
  }

  function renderSectionContent(panel, section) {
    if (!section) {
      panel.appendChild(el(
        "p",
        "rev-empty",
        "This section was not needed for today's update."
      ));
      return;
    }
    if (section.kind === "connections") {
      if (!(section.connections || []).length) {
        panel.appendChild(el("p", "rev-empty", "No related concepts for this update."));
        return;
      }
      renderConnections(panel, section);
      return;
    }
    if (section.kind === "quiz") {
      if (!(section.quiz || []).length) {
        panel.appendChild(el("p", "rev-empty", "No recall questions for this update."));
        return;
      }
      renderQuiz(panel, section);
      return;
    }
    if (!(section.bullets || []).length) {
      panel.appendChild(el(
        "p",
        "rev-empty",
        "This section was not needed for today's update."
      ));
      return;
    }
    renderBullets(panel, section);
  }

  function renderKeyTakeaway(host, remember) {
    if (!remember || !remember.length) { return; }
    var box = el("aside", "key-takeaway");
    box.appendChild(el("p", "key-takeaway-label", "Key takeaway"));
    box.appendChild(el("p", null, remember.slice(0, 2).join(" ")));
    host.appendChild(box);
  }

  function selectSection(state, sectionId) {
    state.activeId = sectionId;
    var catalogue = SECTION_CATALOGUE.find(function (item) {
      return item.id === sectionId;
    }) || SECTION_CATALOGUE[0];
    var sectionMap = state.sectionMap || {};
    var section = sectionMap[sectionId] || null;

    Array.prototype.forEach.call(
      state.nav.querySelectorAll("button"),
      function (button) {
        button.classList.toggle("is-active", button.dataset.sectionId === sectionId);
      }
    );

    var right = state.right;
    right.textContent = "";
    right.appendChild(el("p", "rev-label", catalogue.title));
    right.appendChild(el("h3", "rev-heading", catalogue.heading));
    var panel = el("div", "rev-panel rev-section");
    panel.dataset.sectionId = sectionId;
    renderSectionContent(panel, section);
    right.appendChild(panel);
    if (sectionId !== "recall") {
      renderKeyTakeaway(right, state.remember);
    }
  }

  function buildNotebookShell(host, data, meta) {
    host.textContent = "";

    var top = el("div", "notebook-top");
    var back = el("button", "back-btn", "← Latest updates");
    back.type = "button";
    back.addEventListener("click", showList);
    top.appendChild(back);

    var header = el("header", "article-header");
    var metaRow = el("div", "article-meta");
    if (meta.docType) { metaRow.appendChild(el("span", "pill pill-type", meta.docType)); }
    if (meta.category) { metaRow.appendChild(el("span", "pill pill-category", meta.category)); }
    if (meta.importance) {
      metaRow.appendChild(el(
        "span",
        "pill pill-importance-" + String(meta.importance).toLowerCase(),
        meta.importance
      ));
    }
    header.appendChild(metaRow);
    header.appendChild(el("h2", "article-title", meta.title || ""));
    var sub = el("p", "article-sub");
    if (meta.published) { sub.appendChild(document.createTextNode(meta.published)); }
    if (data.source_url || meta.sourceUrl) {
      var link = el("a", "source-link", "Original RBI source");
      link.href = data.source_url || meta.sourceUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      sub.appendChild(link);
    }
    header.appendChild(sub);
    top.appendChild(header);
    host.appendChild(top);

    var notebook = el("div", "notebook");
    var left = el("div", "nb-page nb-left");
    var gutter = el("div", "nb-gutter");
    gutter.setAttribute("aria-hidden", "true");
    var right = el("div", "nb-page nb-right");

    var nav = el("ul", "section-nav");
    var sectionMap = {};
    (data.sections || []).forEach(function (section) {
      if (section && section.id) {
        sectionMap[section.id] = section;
      }
    });

    var state = {
      nav: nav,
      right: right,
      sectionMap: sectionMap,
      remember: data.remember_this || [],
      activeId: null
    };

    SECTION_CATALOGUE.forEach(function (item) {
      var li = document.createElement("li");
      var button = document.createElement("button");
      button.type = "button";
      button.dataset.sectionId = item.id;
      button.dataset.tone = item.tone;
      button.appendChild(el("span", "sec-num", item.num));
      var copy = el("span", "sec-copy");
      copy.appendChild(el("span", "sec-title", item.title));
      copy.appendChild(el("span", "sec-blurb", item.blurb));
      button.appendChild(copy);
      button.addEventListener("click", function () {
        selectSection(state, item.id);
      });
      li.appendChild(button);
      nav.appendChild(li);
    });

    left.appendChild(nav);
    notebook.appendChild(left);
    notebook.appendChild(gutter);
    notebook.appendChild(right);
    host.appendChild(notebook);

    var firstAvailable = SECTION_CATALOGUE.find(function (item) {
      return !!sectionMap[item.id];
    });
    selectSection(state, (firstAvailable && firstAvailable.id) || "what_happened");
  }

  function openRevision(card) {
    var id = card.dataset.documentId;
    var host = document.getElementById("notebook-root");
    if (!id || !host) { return; }

    var meta = {
      title: card.dataset.title || "",
      category: card.dataset.category || "",
      importance: card.dataset.importance || "",
      docType: card.dataset.docType || "",
      published: card.dataset.published || "",
      sourceUrl: card.dataset.sourceUrl || ""
    };

    showNotebook();
    host.textContent = "";
    host.appendChild(el("p", "revision-status", "Opening your notebook…"));

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
          host.textContent = "";
          host.appendChild(el(
            "p",
            "revision-status",
            result.data.detail || messageForStatus(result.status)
          ));
          var back = el("button", "back-btn", "← Latest updates");
          back.type = "button";
          back.addEventListener("click", showList);
          host.appendChild(back);
          return;
        }
        buildNotebookShell(host, result.data, meta);
      })
      .catch(function () {
        host.textContent = "";
        host.appendChild(el(
          "p",
          "revision-status",
          "Could not load this revision. Try again later."
        ));
      });
  }

  document.addEventListener("click", function (event) {
    var open = event.target.closest(".update-open");
    if (open) {
      var card = open.closest(".update-card");
      if (card) { openRevision(card); }
      return;
    }
  });
})();
""".strip()


def _document_type_label(document_type: str) -> str:
    labels = {
        "press_release": "Press release",
        "notification": "Notification",
        "speech": "Speech",
    }
    return labels.get(document_type, document_type.replace("_", " ").title())


def _supporting_line(document: Document) -> str:
    text = sanitize_plain_text(document.clean_text or "").strip()
    if not text:
        return ""
    for separator in (". ", "? ", "! "):
        if separator in text:
            candidate = text.split(separator, 1)[0].strip()
            if separator.startswith("."):
                candidate = candidate + "."
            elif separator.startswith("?"):
                candidate = candidate + "?"
            else:
                candidate = candidate + "!"
            text = candidate
            break
    if len(text) > 160:
        truncated = text[:157].rsplit(" ", 1)[0].rstrip(",;:")
        return truncated + "…"
    return text


def render_home(documents: Sequence[Document], hours: int = 24) -> str:
    if documents:
        items = "\n".join(_render_item(document) for document in documents)
        updates = '<ol class="updates">\n{}\n</ol>'.format(items)
    else:
        updates = (
            '<p class="empty">Nothing new in the last {} hours.</p>'.format(hours)
        )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "  <title>India Economic Brief</title>\n"
        "  <style>" + _HOME_CSS + "</style>\n"
        "</head>\n"
        "<body>\n"
        '  <div class="app">\n'
        '    <section id="view-list" class="view">\n'
        '      <header class="hero">\n'
        '        <h1 class="brand">India Economic Brief</h1>\n'
        '        <p class="greeting">Good morning. Let’s see what’s moving in the Indian economy.</p>\n'
        "      </header>\n"
        '      <div class="home-layout">\n'
        '        <div class="home-main">\n'
        '          <div class="list-head">\n'
        '            <h2 class="list-label">Latest updates</h2>\n'
        '            <p class="list-sub">First seen in the last '
        + str(hours)
        + " hours</p>\n"
        "          </div>\n"
        "          " + updates + "\n"
        "        </div>\n"
        '        <aside class="brand-side" aria-hidden="true">\n'
        '          <span class="brand-mark"></span>\n'
        "          <p>Neha's own notebook for India’s macro and RBI updates</p>\n"
        "        </aside>\n"
        "      </div>\n"
        "    </section>\n"
        '    <section id="view-notebook" class="view" hidden>\n'
        '      <div id="notebook-root"></div>\n'
        "    </section>\n"
        "  </div>\n"
        "  <script>" + _HOME_JS + "</script>\n"
        "</body>\n"
        "</html>\n"
    )


def _render_item(document: Document) -> str:
    title = escape(polish_display_title(document.title))
    category = escape(document.category)
    importance = escape(document.importance)
    published = escape(document.published_at.date().isoformat())
    url = escape(document.source_url, quote=True)
    doc_type = escape(_document_type_label(document.document_type))
    support = escape(_supporting_line(document))
    importance_class = "pill-importance-{}".format(document.importance.lower())
    item_id = document.id if document.id is not None else ""
    support_html = (
        '<p class="update-support">{}</p>'.format(support) if support else ""
    )
    return (
        '<li class="update-card"'
        ' data-document-id="{item_id}"'
        ' data-title="{title}"'
        ' data-category="{category}"'
        ' data-importance="{importance}"'
        ' data-doc-type="{doc_type}"'
        ' data-published="{published}"'
        ' data-source-url="{url}">'
        '<button type="button" class="update-open" aria-label="Open notebook for {title}">'
        '<div class="update-meta">'
        '<span class="pill pill-type">{doc_type}</span>'
        '<span class="pill pill-category">{category}</span>'
        '<span class="pill {importance_class}">{importance}</span>'
        "</div>"
        '<h3 class="update-title">{title}</h3>'
        "{support_html}"
        '<div class="update-foot">'
        "<span>{published}</span>"
        '<span class="update-open-hint" aria-hidden="true">→</span>'
        "</div>"
        "</button>"
        '<a class="source-link update-source" href="{url}">RBI source</a>'
        "</li>"
    ).format(
        item_id=item_id,
        title=title,
        category=category,
        importance=importance,
        doc_type=doc_type,
        published=published,
        url=url,
        importance_class=importance_class,
        support_html=support_html,
    )
