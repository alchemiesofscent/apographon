# Apographon Orchestrator (Local, No Python)

Goal: produce a single viewer-ready JSON for the entire document using Codex sub-agents only.

Inputs
- Whole-work JSON at data/documents/wellmann.json:
  { "document": {...}, "paragraphs": [ { "id","lang","text","page",... }, ... ] }
- Prompts: prompts/translator_german.md, prompts/translator_latin.md, prompts/translator_greek.md, prompts/improve_pass.md
- Glossaries: glossaries/{german,latin,greek}_decisions.json (optional)

Process per paragraph
1) Select language (de→german, la→latin, el|grc→greek).
2) Spawn translator sub-agent with: id, text, glossary_json (decisions file or {}), utc.
3) Get JSON: english_text, unresolved_tokens, domain_hits, confidence, translator, translated_at_utc, vetting_notes, observations[].
4) Spawn improve-pass agent (copy edit); replace english_text with improved string.
5) Append observations (if any) to glossaries/<lang>_glossary.jsonl with {doc, para, count:1}.
6) Keep the paragraph JSON for merge.

After loop
- Merge all per-paragraph JSON → data/vetted/wellmann-auto.json
- Print summary: high=…, pending_review=…, flagged=…
- Run glossary compaction to refresh *_compiled.json and *_decisions.json

Constraints
- Local only. Deterministic (temperature 0). Sequential. If a sub-agent fails, emit english_text:"", confidence:"flagged", vetting_notes:"error: …".
