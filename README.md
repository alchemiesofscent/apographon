# Apographon Scholarly Reader

Apographon now ships a static, multilingual scholarly text reader that runs on GitHub Pages, plus two helper Python scripts for preparing and vetting translations. The focus is a fully accessible experience for German, Latin, and Greek source texts with aligned English translations—never transliterations.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt  # includes beautifulsoup4
```

## Prerequisites

- `jq` — required for glossary compaction helpers. Install via `sudo apt update && sudo apt install -y jq`.

1. **Convert HTML to JSON**
   ```bash
   python scripts/html_to_json.py data/raw/wellmann.html data/documents/wellmann.json
   ```
   The converter detects paragraph language, column footnotes, and emits JSON conforming to `data/sample.json`.

2. **Trim to the first 15 pages for each batch**
   ```bash
   jq '{document, paragraphs: (.paragraphs | map(select(.page <= 15)))}' \
     data/documents/wellmann.json > data/documents/wellmann_p1_15.json
   ```
   Feed the `_p1_15.json` artifact into the translator.

3. **Drive translations with the LLM orchestrator**
   - Follow `prompts/translator_orchestrator.md` inside the Codex CLI to spawn language agents, run improve passes, and append observations to `glossaries/<lang>_glossary.jsonl`.
   - After the batch, run `make glossary-compact` so compiled and decision files refresh for the next pass.
   - Subsequent runs should load `glossaries/<lang>_decisions.json` as `glossary_json` (or `{}` if absent).

4. **Review in the vetting console**
   - Open `vetting.html` locally, load a JSON file, and step through each paragraph.
   - Approve, flag (requires notes), or skip; export the vetted file and place it under `data/vetted/`.

5. **Publish to GitHub Pages**
   - Commit vetted JSON under `data/vetted/` and deploy.
   - `viewer.html` reads from `data/sample.json` by default—swap the URL or wire a simple index if you host multiple works.

## Project Layout

```
.
├── css/reader.css              # Shared styling for viewer & vetting console
├── js/reader.js                # MultilingualReader class and UI behaviour
├── viewer.html                 # Static reader UI (sticky controls, footnotes, index)
├── vetting.html                # Vetting workspace with contenteditable translations
├── data/
│   ├── sample.json             # Worked sample from Wellmann with German, Latin, Greek
│   ├── documents/.gitkeep      # Place machine-converted JSON here
│   └── vetted/.gitkeep         # Store approved translations here
├── scripts/
│   ├── html_to_json.py         # Converts cleaned HTML to the JSON schema
│   └── translation_pipeline.py # Legacy deterministic stub (testing only)
└── README.md
```

## Reader Highlights (`viewer.html`)

- **Layout controls**: sticky header with search, translation visibility toggles, column/stacked view switch, font-size slider (12–24 px), and Greek font selector (Literata or Arial). Settings persist via `localStorage` along with scroll position.
- **Multilingual rendering**: paragraphs labelled by language with semantic `lang` attributes; Greek defaults to hidden English translations but can be revealed per paragraph or globally.
- **Footnotes**: desktop hover tooltips stay in-bounds; mobile taps open an accessible bottom sheet that locks background scroll. Notes carry both the original text and English translation.
- **Navigation**: generated index with smooth scrolling, URL hash updates, and paragraph-level “Back to index” links. Search filters across original and translated text with live feedback.
- **Accessibility**: system focus styles, labelled controls, ARIA live region announcements, and keyboard access to tooltips/bottom sheets.

## Vetting Console (`vetting.html`)

- Load JSON via file picker or the bundled sample.
- Original text is read-only; the English translation is `contenteditable` for quick adjustments.
- Record vetter name, optional notes, then **Approve** (confidence → high), **Flag** (confidence → flagged, notes required), or **Skip**.
- Visual status cues: green border for approved, red for flagged. Progress indicator tracks `X/Y` paragraphs.
- Export creates a download (`<doc-id>-vetted.json`)—move it into `data/vetted/` before committing.

## Python Utilities

### `html_to_json.py`
- Parses cleaned HTML (expects the Apographon formatter) with BeautifulSoup.
- Detects German vs. Latin vs. Greek paragraphs, extracts footnotes, and creates per-page note identifiers (`page-<n>-note-<n>`).
- Emits JSON with empty English translations but pre-populated metadata, timestamps, and Greek translations disabled by default (`show_by_default: false`).

### Translator orchestrator (LLM workflow)
- Primary workflow is documented in `prompts/translator_orchestrator.md`.
- Processes one paragraph at a time: spawn language agent, run improve pass, merge JSON, and append glossary observations.
- After each batch, run `make glossary-compact` to refresh compiled and decision files for german/latin/greek.
- Feed `glossaries/<lang>_decisions.json` into the next run as `glossary_json` (fall back to `{}` if unavailable).

### Legacy: `translation_pipeline.py` (offline stub)
- Deterministic fallback kept for unit tests or sandboxed demos without LLM access.
- Performs simple dictionary/regex substitutions and confidence scoring but does **not** represent the orchestrated translation quality.

## Working with the Sample Dataset

- `data/sample.json` contains a German narrative paragraph with a translated footnote, a Latin medical excerpt, and a Greek quotation from Galen. All translations are in English and ready to exercise the viewer, vetting console, and scripts.
- Replace the data URL in `viewer.html` or load your own document via the console to validate end-to-end behaviour.

## Deployment Tips

- Serve the project locally (`python -m http.server`) to emulate GitHub Pages.
- Keep large JSON documents under `data/documents/` (machine output) and copy only vetted, human-reviewed files into `data/vetted/` before publishing.
- Cache busting: update the query string (e.g., `data/sample.json?v=2`) when you deploy new data so browsers fetch the latest translation set.

## License

MIT — see [`LICENSE`](LICENSE).
