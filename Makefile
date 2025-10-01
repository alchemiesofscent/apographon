# Makefile for German Book Converter

.PHONY: all clean build_epub validate_tei deps

all: build_epub validate_tei

build_epub:
	@echo "Building EPUB from cleaned HTML..."
	./scripts/build_epub.sh

validate_tei:
	@echo "Validating TEI XML..."
	./scripts/validate_tei.sh

clean:
	@echo "Cleaning up processed files..."
	rm -rf data/processed/*

glossary-compact:
	@chmod +x scripts/glossary_compact.sh
	@for L in german latin greek; do scripts/glossary_compact.sh $$L; done

deps:
	sudo apt update && sudo apt install -y jq
