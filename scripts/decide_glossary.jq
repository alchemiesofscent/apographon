# Input: compiled array from compact_glossary.jq
# Output: {"Schule":{"preferred":"school","alternates":[...],"stats":[...]}, ...}
# Usage: jq -f scripts/decide_glossary.jq glossaries/german_compiled.json > glossaries/german_decisions.json
reduce .[] as $e ({}; .[$e.src] = {
  preferred: ($e.choices[0].cand // null),
  alternates: ( ($e.choices[1:] // []) | map(.cand) ),
  stats: $e.choices
})
