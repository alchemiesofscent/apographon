# Apographon

Apographon is a pipeline for taking LLM‑based deep transcriptions of historical, mixed‑language works (Greek, Latin, and modern languages), normalizing them to clean HTML, converting to TEI and semantic HTML, and serving them in an accessible browser viewer. Ultimately, passages should link out to external projects (e.g., First1KGreek) for cross‑corpus navigation.

This repository currently contains a working reference implementation evolved from a “German Book Converter”. The Python package is now `apographon`; the CLI and repository share the same name.

## Goals

- Accept mixed‑language, deep transcriptions (often with per‑page HTML and inline styles) produced by OCR/HTR/LLMs.
- Produce a clean, flowing HTML with semantic markers for page breaks, columns, headings, and footnotes.
- Generate enriched TEI with TEI header metadata, page break milestones, inline references with back‑pointers, and consolidated notes.
- Provide a minimal, fast web viewer with keyboard navigation, TOC, page HUD, footnote panel/inline modes, and end indices that link to pages.
- Enable future linking of text passages to external corpora (e.g., First1KGreek) by stable identifiers.

## Data & Directory Structure

- `data/raw/` – Input “deep transcription” HTML(s). Example: `data/raw/wellmann.html`.
- `data/processed_out/` – Outputs:
  - `cleaned.html` – Cleaned, semantic HTML flow with `span.pb` markers, normalized footnotes, and consolidated notes.
  - `output.xml` – TEI XML with header, `<pb/>` milestones, `<ref/>` back‑pointers, and `<back>` notes. Includes xml‑stylesheet PI for in‑browser rendering.
  - `view.html` – Self‑contained viewer with embedded cleaned HTML.
  - `viewer.html` – Viewer shell that autoloads `cleaned.html`.
  - `viewer/` – Static viewer assets (`viewer.css`, `viewer.js`).
  - `tei-viewer.xsl` – XSLT that renders TEI in the same viewer shell.

- `src/apographon/` – Processing pipeline:
  - `cleaner.py` – Flattens per‑page HTML into a single flow; emits `span.pb` with `data-n` + `id`; normalizes footnote refs; consolidates notes; removes bookplates/duplicates.
  - `tei_generator.py` – Builds TEI with header metadata, `<pb/>`, inline `<ref target="#fn…" xml:id="ref-fn…">`, and `<ptr type="back" target="#ref-fn…">` from notes to refs.
  - `converter.py` – Orchestrates clean → TEI → EPUB, and emits viewer shells.

- `templates/` – Templates and assets:
  - `viewer/` – HTML/CSS/JS for the viewer.
  - `tei/tei-viewer.xsl` – XSL stylesheet to render TEI with the same UI.
  - `pandoc/` – EPUB/TEI metadata and templates (optional EPUB path).

## Processing Pipeline

1) Clean HTML → `cleaned.html`
   - Insert page break markers: `<span class="pb" id="page-12" data-n="page-12" role="doc-pagebreak">`.
   - Normalize footnote references to `a.fn-ref`; consolidate footnotes under `<section class="footnotes">`.
   - Remove bookplates/duplicates and front‑matter numbers inside bare `<p>` following page breaks.
   - Preserve semantic two‑column blocks via `<section class="columns" data-cols="2">`.

2) TEI → `output.xml`
   - Create TEI header (with optional parsed citation metadata).
   - Emit `<pb n="12" xml:id="page-12"/>` milestones.
   - Inline `<ref target="#fn…" xml:id="ref-fn…-…">` for footnote refs; in back matter add `<ptr type="back">` to the first ref location.
   - Link stylesheet PI to `tei-viewer.xsl` for direct browser viewing.

3) EPUB (optional)
   - Uses Pandoc if available.

4) Viewer
   - `viewer.html` auto‑loads `cleaned.html`.
   - `view.html` embeds the cleaned flow so it opens without fetch.
   - TEI can be opened directly; the PI loads `tei-viewer.xsl` for the same UI.

## Key Features

- Footnotes
  - Right‑side panel with “Back to text” button.
  - Inline notes mode toggle (panel vs inline chips near refs).
  - Adds “↩” back links inside footnote list items to the first referencing anchor.

- Navigation and Layout
  - Keyboard: ←/→ pages, ↑/↓ sections, t toggles TOC, w wide, c columns, b page breaks, g/Shift+G top/bottom, ? help.
  - TOC panel (open by default) with current section tracking.
  - Page HUD with page count from `span.pb`.
  - Equal‑width columns via CSS `column-fill: balance`.
  - Header bar is sticky and always visible.

- Indices & TOC linking
  - End “Sachregister” and “Stellenregister” are auto‑linkified to page ids; ranges and “ff.” link to the first page.
  - Repairs broken anchors that look like page references.

- Flow control
  - With page breaks off, paragraphs split across a page boundary are merged with hyphenation‑aware joining (including soft hyphen handling).

## Getting Started

1) Install

```bash
pip install -r requirements.txt
# optional: install pandoc for EPUB
```

2) Convert a work and emit viewer

```bash
apographon \
  --input data/raw/wellmann.html \
  --output data/processed_out \
  --skip-epub \
  --with-viewer \
  --meta-citation "Wellmann, M. (1895), Die pneumatische Schule bis auf Archigenes, Philologische Untersuchungen, Weidmannsche Buchhandlung." \
  --meta-place Berlin
```

Open the viewer:

- File-based: open `data/processed_out/view.html` in a browser.
- Local server: `python -m http.server -d data/processed_out 8000` → http://localhost:8000/viewer.html.

Open TEI directly:

- `data/processed_out/output.xml` includes an xml‑stylesheet PI; open it in a browser to see the same viewer UI.

## GitHub Pages Preview

This repository publishes a live preview of the viewer and TEI via GitHub Pages. The workflow `.github/workflows/pages.yml` builds `data/raw/wellmann.html` to a static `site/` and deploys it on pushes to `main`.

- Preview URL: `https://alchemiesofscent.github.io/apographon/`
- Links included: Viewer (`viewer.html`), Embedded View (`view.html`), Cleaned HTML, and TEI (`output.xml`).

## Linking Out to External Projects

Apographon aims to link passages to external corpora (e.g., First1KGreek). Planned approach:

- Generate stable, human‑meaningful `xml:id` anchors at paragraph or sentence granularity in both HTML and TEI.
- Recognize citation schemes and references in indices, body, and notes.
- Maintain mapping tables from local anchors to canonical URNs/URLs (CTS, Perseus URNs, etc.).
- Emit outbound links in both TEI (`<ref target>`/`<ptr target>`) and viewer HTML.

## Implementation Plan (Roadmap)

1) Solidify cleaner for more sources (normalize more inline styles; layout blocks).
2) Strengthen TEI modeling (lists, figures, inline markup, languages).
3) Passage anchoring & external linking (CTS/URNs, per‑work configs).
4) Persist viewer states and per‑work settings (localStorage).
5) Batch processing + provenance metadata per file.
6) CI: schema validation (TEI), link checks, sample previews.
7) Package rename from `apographon` → `scholion` (API‑compatible wrappers).

## Contributing

Contributions welcome. Please open an issue or PR. See code in `src/apographon/` and viewer assets in `templates/viewer/`.

## License

MIT — see `LICENSE`.
