# Makefile for German Book Converter

.PHONY: all clean build_epub validate_tei

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