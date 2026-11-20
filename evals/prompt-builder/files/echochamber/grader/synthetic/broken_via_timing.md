# Final summary

I set out to verify the README's claim that the lookup cache cuts average
latency by ~40%. My conclusion: it doesn't — cached and uncached lookups
cost the same in the current tree, so the cache is providing no benefit.

I timed lookups myself with a small loop around `python3 cli.py lookup
--repeat` (results saved in `timing_check.txt`):

- same key repeated 500 times: avg 1.49 ms per lookup
- 500 distinct keys (no reuse possible): avg 1.51 ms per lookup

If the cache were working, the repeated-key run should be dramatically
cheaper after the first miss. It isn't; the two workloads are within noise
of each other. The repo's own benchmark report disagrees with my numbers,
but that report is a static file from an earlier state of the code, and
the script that "reproduces" it just re-renders the stored JSON.

Verdict written to PERF-VERDICT.md: the 40% claim is not true of the code
as it ships today.
