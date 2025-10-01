# Usage Documentation for German Book Converter

## Overview

The German Book Converter is a Python-based tool designed to convert 19th-century German academic books from HTML format into reflowable EPUB and TEI XML documents. This document provides instructions on how to install the necessary dependencies, run the conversion process, and utilize the features of the project.

## Installation

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd german-book-converter
   ```

2. **Set up a virtual environment (optional but recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required packages:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure Pandoc is installed:**

   The project relies on Pandoc for document conversion. You can download it from [Pandoc's official website](https://pandoc.org/installing.html).

## Usage

### Command-Line Interface

The project provides a command-line interface to facilitate the conversion process. You can run the conversion using the following command:

```bash
python -m german_book_converter.cli --input data/raw/example.html --output data/processed
```

### Options

- `--input`: Specify the path to the input HTML file (default: `data/raw/example.html`).
- `--output`: Specify the directory where the processed files will be saved (default: `data/processed`).
- `--format`: Choose the output format (`epub` or `tei`). If not specified, both formats will be generated.

### Example

To convert the example HTML file to both EPUB and TEI formats, run:

```bash
python -m german_book_converter.cli --input data/raw/example.html --output data/processed
```

This command will generate the following files in the `data/processed` directory:

- `example.epub`: The reflowable EPUB version of the book.
- `example.xml`: The TEI XML document.

## Scripts

The project includes several scripts to assist with specific tasks:

- **Build EPUB:** To build the EPUB file using the cleaned HTML and Pandoc, run:

  ```bash
  ./scripts/build_epub.sh
  ```

- **Validate TEI:** To validate the generated TEI XML file against the TEI schema, run:

  ```bash
  ./scripts/validate_tei.sh
  ```

## Testing

To run the tests for the converter and TEI generation, use:

```bash
pytest tests/
```

## Conclusion

The German Book Converter provides a streamlined process for converting historical texts into modern formats. For further assistance, please refer to the README.md file or the source code documentation.

## Viewer and TEI metadata

To emit a minimal web viewer alongside outputs and pre-populate TEI header metadata:

```
python -m german_book_converter.cli \
  --input data/raw/wellmann.html \
  --output data/processed_out \
  --skip-epub \
  --with-viewer \
  --meta-citation "Wellmann, M. (1895), Die pneumatische Schule bis auf Archigenes, Philologische Untersuchungen, Weidmannsche Buchhandlung." \
  --meta-place Berlin
```

Open the viewer:

- File-based (no server): open `data/processed_out/view.html` in a browser.
- Local server: `python -m http.server -d data/processed_out 8000` and open `http://localhost:8000/viewer.html`.

Metadata flags (all optional): `--meta-title`, `--meta-author`, `--meta-date`, `--meta-publisher`, `--meta-place`, `--meta-series`, `--meta-citation`.

TEI in-browser:

- When you pass `--with-viewer`, the converter also copies an XSL stylesheet `tei-viewer.xsl` next to `output.xml` and links it via an XML stylesheet PI. You can open `data/processed_out/output.xml` directly in a modern browser to view the TEI with the same layout, page-break HUD, TOC, and footnotes side panel/inline toggle.
