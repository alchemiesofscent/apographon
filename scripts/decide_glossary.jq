reduce .[] as $e ({}; .[$e.src] = {
  preferred: ($e.choices[0].cand // null),
  alternates: ( ($e.choices[1:] // []) | map(.cand) ),
  stats: $e.choices
})
