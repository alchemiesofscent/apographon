# Makefile for German Book Converter

.PHONY: all clean validate_tei deps glossary-compact

all: validate_tei

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
