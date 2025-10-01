#!/usr/bin/env bash
set -euo pipefail
lang="${1:?lang (german|latin|greek)}"
jsonl="glossaries/${lang}_glossary.jsonl"
compiled="glossaries/${lang}_compiled.json"
decisions="glossaries/${lang}_decisions.json"

[ -s "$jsonl" ] || { echo "no $jsonl; nothing to compact"; exit 0; }
jq -s -f scripts/compact_glossary.jq "$jsonl" > "$compiled"
jq -f scripts/decide_glossary.jq "$compiled" > "$decisions"
echo "wrote $compiled and $decisions"
