# Repository Guidelines

## Project Structure & Module Organization
Core pipeline modules live in `src/apographon/` (converter, generators, CLI). Shared automation is in `scripts/` (shell wrappers, jq filters) invoked by the Makefile. Static reader assets (`css/`, `js/`, `viewer.html`, `vetting.html`) rely on vetted JSON. Data flows from `data/raw/` ➜ `processed/` ➜ `documents/` ➜ `vetted/`. Supporting references live in `docs/`, `prompts/`, `glossaries/`, while tests and fixtures sit in `tests/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create the virtualenv.
- `pip install -r requirements.txt`: install runtime and test deps.
- `python scripts/html_to_json.py data/raw/<file>.html`: convert cleaned HTML to Apographon JSON.
- `make validate_tei`: run TEI schema validation via the shell helper.
- `make glossary-compact`: rebuild glossary decision + compiled files.
- `pytest`: execute the test suite; narrow with `-k` during iteration.

## Coding Style & Naming Conventions
Target PEP 8: four-space indents, snake_case functions, PascalCase classes, f-strings for formatting. Modules should describe their role (`converter.py`, `tei_generator.py`). CLI options stay kebab-case and flow through argparse consistently. Mirror existing front-end naming (BEM-ish CSS, camelCase JS). Persist lowercase underscore naming for JSON artifacts and glossary filenames.

## Testing Guidelines
Pytest discovers tests under `tests/`, even though many suites subclass `unittest.TestCase`. Extend the nearest fixture-backed test or add a focused module-level file when covering new behavior. Include regression assertions for both success and error scenarios. Run `pytest` before every PR and attach failure details if fixes land later.

## Commit & Pull Request Guidelines
Commits use short, imperative subjects under 72 characters (e.g., “Limit viewer fonts”). Keep each commit self-contained: code, tests, and any regenerated data. PRs should supply a concise summary, linked issues, command outputs or screenshots for reader/UI changes, and a note on regenerated files or external requirements (e.g., xmllint) that reviewers may need.

## Data & Workflow Notes
Raw HTML stays immutable in `data/raw/`; derived assets belong in `processed/` or `documents/`, and only human-reviewed JSON is stored in `vetted/`. After translator runs, call `make glossary-compact` so orchestration and the reader pick up the latest terminology decisions. When publishing, confirm `viewer.html` references the intended vetted document and mention cache-busting steps if applicable.
