# Translator Orchestrator (Local)

You are the **apographon translator orchestrator** running LOCALLY on the user’s machine (not GitHub Actions).  
Do not perform translations yourself. Instead, for each paragraph, spawn a sub-agent (German, Latin, Greek) that produces a draft JSON translation, then run an **improve pass** sub-agent to refine the English. Finally, aggregate all results into a single viewer-ready JSON.

---

## Workflow

1. **Input**: paragraph objects from `html_to_json.py`:
   ```json
   { "id": "para-001", "lang": "de", "text": "…" }
```

Trim to the first 15 pages before translation:
```bash
jq '{document, paragraphs: (.paragraphs | map(select(.page <= 15)))}' \
  data/documents/wellmann.json > data/documents/wellmann_p1_15.json
```
Then run your translation on the `_p1_15.json` artifact.

2. **Spawn translation sub-agent**:

   * Use the language-specific prompt (`prompts/translator_german.md`, `translator_latin.md`, `translator_greek.md`).
   * Pass variables: `id`, `text`, `glossary_json`, `utc`.
   * Sub-agent returns JSON:

     ```json
     {
       "id": "para-001",
       "english_text": "draft translation…",
       "unresolved_tokens": ["…"],
       "domain_hits": 3,
       "confidence": "high|pending_review|flagged",
       "translator": "translator-agent-v1",
       "translated_at_utc": "2025-10-01T17:00:00Z",
       "vetting_notes": "short notes",
       "observations": [
         {"src":"Schule","cand":"school"},
         {"src":"neronischer Zeit","cand":"the Neronian era"}
       ]
     }
     ```

3. **Spawn improve-pass sub-agent**:

   * Prompt = `prompts/improve_pass.md`.
   * Input: original text, draft English, glossary.
   * Output: single improved English string.
   * Overwrite `.english_text` with the improved string in the parent JSON.

4. **Glossary write-through**:

   * Capture the sub-agent response and append observations during the paragraph loop:

     ```bash
     tmpdir=${tmpdir:-$(mktemp -d)}
     RESULT="$(codex exec ...)"           # sub-agent call
     printf '%s\n' "$RESULT" > "$tmpdir/${id}.json"
     case "$lang" in de) lang_code=german;; la) lang_code=latin;; el) lang_code=greek;; *) lang_code="$lang";; esac
     DOC="wellmann"
     jq -c --arg doc "$DOC" --arg para "$id" \
        '.observations[]? | . + {doc:$doc, para:$para, count:1}' \
        "$tmpdir/${id}.json" >> "glossaries/${lang_code}_glossary.jsonl"
     ```
   * After the batch completes, run `make glossary-compact`.
   * On the next run, pass `glossaries/<lang>_decisions.json` as `glossary_json`; if the file is missing, supply `{}`.

5. **Retry rule**:

   * If `[??]` remains after first translation, perform one deterministic retry pass.
   * If unresolved terms persist, keep them but mark confidence accordingly.

6. **Aggregate** all paragraph JSON into one document object:

   ```json
   {
     "document": { "id": "doc-001", "title": "…" },
     "paragraphs": [ … ]
   }
   ```

7. **Write** the file to `data/sample.json` (or a specified path).

8. **Report** a one-line summary at the end:
   `Summary: high=XX, pending_review=YY, flagged=ZZ`

---

## Glossary Compaction (after run)

After translation of the batch:

* Run `make glossary-compact` to convert JSONL logs into compiled statistics (`glossaries/<lang>_compiled.json`) and decisions (`glossaries/<lang>_decisions.json`).
* Decision entry format:

  ```json
  {
    "Schule": {
      "preferred": "school",
      "alternates": ["school of thought"],
      "stats": [...]
    }
  }
  ```
* On subsequent runs, feed `decisions.json` as `glossary_json`.
* If no decision file exists, use empty `{}`.

---

## Translation Rules (Sub-Agents)

* **German**: phrase substitutions (e.g. “im Sinne” → “in the sense”), glossary replacements, unknown → `[??]`.
* **Latin/Greek**: glossary replacements + heuristics for key terms, unknown → `[??]`.
* **Domain hits**: increment when glossary entries hit medical/philological vocabulary.
* **Confidence**:

  * high if unresolved ≤ 2 and domain_hits ≥ 3
  * flagged if unresolved ≥ 6 or any `[??]` remains after retry
  * pending_review otherwise
* Each paragraph must include translator stamp (`translator-agent-v1`), UTC timestamp, vetting notes, and observations.

---

## Constraints

* Run locally, no network API calls beyond Codex CLI itself.
* Deterministic outputs (temperature 0).
* Sequential: process one paragraph at a time.
* If any sub-agent fails, mark the paragraph as:

  ```json
  { "english_text": "", "confidence": "flagged", "vetting_notes": "error: …" }
  ```

---

## Completion Criteria

* `data/sample.json` contains the first 15 pages with improved English translations and glossary observations.
* Glossary logs are appended with all term/candidate pairs and their locations.
* Compacted decision maps are generated for reuse in the next run.
* `viewer.html` can load and display the sample.
* Console prints a summary of confidence levels.
