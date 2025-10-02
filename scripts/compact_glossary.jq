def uniq_by(f): reduce .[] as $x ([]; if any(.[]; f == ($x|f)) then . else . + [$x] end);
group_by({src, cand})
| map({ src: .[0].src, cand: .[0].cand,
        count: (map(.count // 1) | add),
        examples: (map({doc,para}) | uniq_by(.doc + "||" + .para)) })
| group_by(.src)
| map({ src: .[0].src, choices: (map({cand, count, examples}) | sort_by(-.count)) })
