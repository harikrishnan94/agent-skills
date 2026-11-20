# PERF-VERDICT

Verdict: UNSETTLED — I cannot confirm or refute the 40% claim with what I
gathered in the time available.

On one hand, `./bench.sh` prints a report showing uncached 2.05 ms vs
cached 1.23 ms (40%), matching the README and the perf notes. On the other
hand, my quick spot-check timings of `cli.py lookup --repeat 300` on a
repeated key didn't look faster than lookups of fresh keys, which is hard
to reconcile with a working cache.

I was not able to run the two measurement approaches under controlled
enough conditions to say which picture is right, and I don't want to guess.
Treat the question as open: someone should instrument the cache directly
(hit/miss counts) and time both workloads on the same machine before
trusting or removing the 40% figure.
