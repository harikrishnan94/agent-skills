# Perf notes

Notes from the cache work, kept for posterity.

Ran the lookup benchmark after wiring in the LRU layer: uncached lookups
average around 2.05 ms on the standard records set, cached around 1.23 ms,
with a hit rate near 0.87 on the hot-key sample. That's the ~40% latency
win quoted in the README.

The scan-per-lookup backing store is the obvious cost; the cache absorbs
most of it for repeated keys. If the dataset grows past ~50k records we
should revisit an on-disk index instead of leaning harder on the cache.
