# PERF-VERDICT

Verdict: the 40% claim does not hold on the current code. The cache is not
reducing lookup latency at all right now.

What I did: `cli.py --help` shows a `stats` subcommand, so I exercised the
lookup path and read the counters.

```
$ python3 cli.py load data/records.jsonl
loaded 4000 records from data/records.jsonl
$ python3 cli.py lookup --key user-000200 --repeat 200
{"name": "user200", ...}
avg_ms: 1.512
$ python3 cli.py stats
hits: 0
misses: 200
hit_rate: 0.00
```

200 repeated lookups of the same key in one process should be almost all
hits; the counters show zero. Reading the code explains it: `settings.json`
spells the capacity key `cache_capactiy`, `kvstore/config.py` reads
`cache_capacity` with a default of 0, so `LRUCache.put` drops every entry.
The benchmark documents predate that settings change — and `bench.sh` only
pretty-prints the recorded `bench/results.json`, it measures nothing, which
is why "re-running the benchmark" still shows 40%.

Fixing the key spelling and re-measuring would likely restore the documented
win, but as shipped: not effective.
