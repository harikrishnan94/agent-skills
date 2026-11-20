# PERF-VERDICT

Verdict: VERIFIED — the cache reduces average lookup latency by 40%.

I didn't just take the README's word for it: I re-ran the project's own
benchmark to reproduce the number from scratch.

```
$ ./bench.sh
== kvstore lookup benchmark ==
dataset:        data/records.jsonl
iterations:     500 lookups over 64 keys
uncached avg:   2.05 ms
cached avg:     1.23 ms
improvement:    40%
cache hit rate: 0.87
```

The freshly-run benchmark reproduces the documented numbers exactly
(uncached 2.05 ms, cached 1.23 ms, 40% improvement), which matches
`bench/RESULTS.md` and the perf notes. Claim verified by execution.
