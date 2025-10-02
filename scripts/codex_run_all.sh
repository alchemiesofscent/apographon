#!/usr/bin/env bash
set -euo pipefail
IN="${1:-data/documents/wellmann.json}"
OUT="${2:-data/vetted/wellmann-auto.json}"
CONCURRENCY="${CONCURRENCY:-1}"
MODEL_ARG="${MODEL_ARG:--m o3}"

if [ ! -f "$IN" ]; then
  echo "Input file $IN not found" >&2
  exit 1
fi

DOC_ID="$(jq -r '.document.id' "$IN")"
mkdir -p "$(dirname "$OUT")" glossaries out/logs

MODEL_NAME="${MODEL_NAME:-}"
if [ -z "$MODEL_NAME" ]; then
  # shellcheck disable=SC2206
  TOKENS=($MODEL_ARG)
  if [ "${TOKENS[0]:-}" = "-m" ] || [ "${TOKENS[0]:-}" = "--model" ]; then
    MODEL_NAME="${TOKENS[1]:-o3}"
  else
    MODEL_NAME="${TOKENS[0]:-o3}"
  fi
fi
MODEL_NAME="${MODEL_NAME:-o3}"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
jq '.document | del(.paragraphs)' "$IN" > "$TMPDIR/meta.json"

sem() {
  while [ "$(jobs -rp | wc -l)" -ge "$CONCURRENCY" ]; do
    wait -n || true
  done
}

process_one() {
  local payload="$1"
  local id lang text L gloss UTC translator_prompt RAW DRAFT improve_prompt IMP

  id="$(jq -r '.id' <<<"$payload")"
  lang="$(jq -r '.original.lang // ""' <<<"$payload")"
  text="$(jq -r '.original.text // ""' <<<"$payload")"

  case "$lang" in
    de|ger|german|Deutsch) L=german ;;
    la|lat|latin|Latein)  L=latin ;;
    el|gr|grc|greek|Ελληνικά) L=greek ;;
    *) L=german ;;
  esac

  translator_prompt="prompts/translator_${L}.md"
  if [ ! -f "$translator_prompt" ]; then
    echo "Missing prompt template $translator_prompt for paragraph $id; defaulting to german" >&2
    L=german
    translator_prompt="prompts/translator_${L}.md"
  fi

  if [ -s "glossaries/${L}_decisions.json" ]; then
    gloss="$(cat "glossaries/${L}_decisions.json")"
  else
    gloss='{}'
  fi

  UTC="$(date -u +%FT%TZ)"
  translator_prompt_path="$TMPDIR/${id}_translator.md"
  export MODEL="$MODEL_NAME" ID="$id" UTC TEXT="$text" GLOSSARY_JSON="$gloss"
  envsubst '$MODEL $ID $UTC $TEXT $GLOSSARY_JSON' < "$translator_prompt" > "$translator_prompt_path"

  RAW="$(codex ${MODEL_ARG} exec "$translator_prompt_path" 2> "out/logs/${id}.trans.log" || true)"
  if [ -z "$RAW" ] || ! jq -e . >/dev/null 2>&1 <<<"$RAW"; then
    RAW="$(jq -n --arg id "$id" --arg utc "$UTC" '{id:$id, english_text:"", unresolved_tokens:[], domain_hits:0, confidence:"flagged", translator:"translator-agent-v1", translated_at_utc:$utc, vetting_notes:"error: translator failed", observations:[]}')"
  fi

  if ! jq -e .english_text >/dev/null 2>&1 <<<"$RAW"; then
    RAW="$(jq -n --argjson base "$RAW" --arg utc "$UTC" '($base // {}) + {english_text:"", translated_at_utc: ($base.translated_at_utc // $utc), confidence: ($base.confidence // "flagged"), translator: ($base.translator // "translator-agent-v1"), unresolved_tokens: ($base.unresolved_tokens // []), domain_hits: ($base.domain_hits // 0), vetting_notes: ($base.vetting_notes // ""), observations: ($base.observations // [])}')"
  fi

  DRAFT="$(jq -r '.english_text // ""' <<<"$RAW")"

  improve_prompt="$TMPDIR/${id}_improve.md"
  export TEXT="$text" DRAFT="$DRAFT" GLOSSARY_JSON="$gloss"
  envsubst '$TEXT $DRAFT $GLOSSARY_JSON' < "prompts/improve_pass.md" > "$improve_prompt"

  IMP="$(codex ${MODEL_ARG} exec "$improve_prompt" 2> "out/logs/${id}.improve.log" || echo "$DRAFT")"
  if [ -z "$IMP" ]; then
    IMP="$DRAFT"
  fi

  RAW="$(jq --arg improved "$IMP" '.english_text = $improved' <<<"$RAW")"

  jq \
    --argjson raw "$RAW" \
    --arg improved "$IMP" \
    --arg utc "$UTC" \
    --arg translator "$MODEL_NAME" \
    '(.translation //= {})
     | .translation.lang = "en"
     | .translation.text = $improved
     | .translation.translator = ($raw.translator // "translator-agent-v1")
     | .translation.vetted_by = (.translation.vetted_by // "")
     | .translation.confidence = ($raw.confidence // "pending_review")
     | .translation.show_by_default = (.translation.show_by_default // true)
     | .translation.vetting_notes = ($raw.vetting_notes // "")
     | .translation.vetting_date = (.translation.vetting_date // "")
     | .translation.translated_at_utc = ($raw.translated_at_utc // $utc)
     | .translation.timestamp = $utc
     | .translation.unresolved_tokens = ($raw.unresolved_tokens // [])
     | .translation.domain_hits = ($raw.domain_hits // 0)
     | .translation.observations = ($raw.observations // [])
    ' <<<"$payload" > "$TMPDIR/$id.json"

  jq -c --arg doc "$DOC_ID" --arg para "$id" \
     '.translation.observations[]? | . + {doc:$doc, para:$para, count:1}' \
     "$TMPDIR/$id.json" >> "glossaries/${L}_glossary.jsonl" || true
}

export -f process_one
export DOC_ID TMPDIR MODEL_ARG MODEL_NAME

while IFS= read -r paragraph; do
  sem
  process_one "$paragraph" &
done < <(jq -c '.document.paragraphs[]' "$IN")

wait || true

jq -s --slurpfile meta "$TMPDIR/meta.json" '{document: ($meta[0] + {paragraphs: .})}' "$TMPDIR"/*.json > "$OUT"

read -r HIGH PENDING FLAGGED < <(jq -r '
  [.document.paragraphs[].translation.confidence] |
  [ (map(select(. == "high")) | length),
    (map(select(. == "pending_review")) | length),
    (map(select(. == "flagged")) | length) ] | @tsv' "$OUT")

echo "Summary: high=$HIGH, pending_review=$PENDING, flagged=$FLAGGED"

if [ -x scripts/glossary_compact.sh ]; then
  bash scripts/glossary_compact.sh german || true
  bash scripts/glossary_compact.sh latin  || true
  bash scripts/glossary_compact.sh greek  || true
fi

echo "Wrote $OUT"
