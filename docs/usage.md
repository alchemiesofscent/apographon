# Usage Documentation for Apographon

## Overview
Apographon converts 19th-century German academic HTML into a cleaned HTML surrogate, rich TEI XML, and an optional static reader. This guide explains how to install dependencies, run the command-line interface, and validate the generated outputs.

## Installation
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd apographon
   ```
2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```
3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Install XML tooling (optional but useful)**
   - `xmllint` validates TEI output: `sudo apt install -y libxml2-utils`

## Usage
### Command-Line Interface
Run the converter directly via the CLI module:
```bash
python -m apographon.cli --input data/raw/example.html --output data/processed
```
### Options
- `--input`: Path to the source HTML file (defaults to `data/raw/example.html`).
- `--output`: Directory for cleaned HTML and TEI results (defaults to `data/processed`).
- `--with-viewer`: Copy a minimal static reader and emit `viewer.html`/`view.html` next to the TEI.
- Metadata flags (optional): `--meta-title`, `--meta-author`, `--meta-date`, `--meta-publisher`, `--meta-place`, `--meta-series`, `--meta-citation`.

### Example Output
Running the command above produces:
- `cleaned.html`: Normalized HTML produced by the cleaning pass.
- `output.xml`: TEI XML enriched with metadata, references, and structured notes.
- Optional viewer assets when `--with-viewer` is supplied (`viewer/`, `viewer.html`, `view.html`, `tei-viewer.xsl`).

## Scripts and Make Targets
- `make validate_tei`: Run the TEI validation wrapper (`scripts/validate_tei.sh`).
- `make glossary-compact`: Refresh glossary decision and compiled files for downstream translation workflows.

## Testing
Execute the unit suite with:
```bash
pytest tests/
```
Target specific tests during development with `pytest tests/test_converter.py -k <keyword>`.

## Viewer and TEI Metadata
To emit the static reader and populate common TEI metadata fields in one run:
```bash
python -m apographon.cli \
  --input data/raw/wellmann.html \
  --output data/processed_out \
  --with-viewer \
  --meta-citation "Wellmann, M. (1895), Die pneumatische Schule bis auf Archigenes, Philologische Untersuchungen, Weidmannsche Buchhandlung." \
  --meta-place Berlin
```
Open the viewer by loading `data/processed_out/view.html` in a browser, or serve the folder with `python -m http.server -d data/processed_out 8000` and visit `http://localhost:8000/viewer.html`. When `tei-viewer.xsl` is copied alongside `output.xml`, modern browsers can render the TEI directly.
