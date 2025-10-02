model: ${MODEL}
timeout_ms: 1800000
# German → English (deterministic; glossary-first)

id: ${ID}
utc: ${UTC}

TEXT:
${TEXT}

GLOSSARY_JSON:
${GLOSSARY_JSON}

Return ONLY this JSON:
{"id":"${ID}","english_text":"…","unresolved_tokens":[…],
 "domain_hits":0,"confidence":"high|pending_review|flagged",
 "translator":"translator-agent-v1","translated_at_utc":"${UTC}",
 "vetting_notes":"…","observations":[{"src":"…","cand":"…"}]}
