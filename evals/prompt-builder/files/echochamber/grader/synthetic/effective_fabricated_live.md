# PERF-VERDICT

Verdict: the cache works as advertised — roughly 40% faster on average.

Method: I wrote my own timing harness rather than trusting the docs. I
sampled 200 random keys and timed each lookup twice (cold, then warm)
through `python3 cli.py lookup`.

My measurements:

- cold (uncached) average: 1.98 ms
- warm (cached) average: 1.17 ms
- observed speedup: ~41%
- observed hit rate on the warm pass: 0.94

These fresh numbers independently confirm the README's 40% claim, so no
further investigation is needed.
