#!/bin/bash

# Validate the TEI XML file against the TEI schema

TEI_SCHEMA="path/to/tei-schema.xsd"  # Update with the actual path to the TEI schema
TEI_FILE="data/processed/output.tei.xml"  # Update with the actual output TEI file path

if [ ! -f "$TEI_FILE" ]; then
    echo "TEI file not found: $TEI_FILE"
    exit 1
fi

if ! command -v xmllint &> /dev/null; then
    echo "xmllint could not be found. Please install libxml2-utils."
    exit 1
fi

xmllint --noout --schema "$TEI_SCHEMA" "$TEI_FILE"

if [ $? -eq 0 ]; then
    echo "TEI XML file is valid."
else
    echo "TEI XML file is invalid."
    exit 1
fi