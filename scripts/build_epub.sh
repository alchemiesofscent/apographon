#!/bin/bash

# Check if the necessary input HTML file exists
INPUT_FILE="data/raw/example.html"
OUTPUT_DIR="data/processed"
EPUB_OUTPUT="output/book.epub"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Input file not found: $INPUT_FILE"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Convert HTML to EPUB using Pandoc
pandoc "$INPUT_FILE" -o "$EPUB_OUTPUT" --metadata-file=templates/pandoc/epub_metadata.yaml --css=templates/css/epub_styles.css

if [ $? -eq 0 ]; then
    echo "EPUB file created successfully: $EPUB_OUTPUT"
else
    echo "Failed to create EPUB file."
    exit 1
fi