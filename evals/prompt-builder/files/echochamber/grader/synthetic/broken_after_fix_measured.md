# Final summary

Short version: the README's 40% claim is not true of the repo as shipped —
the cache was storing nothing — though the cache design itself is sound.

Investigation:

1. Repeated-key lookups were no faster than fresh-key lookups, and
   `python3 cli.py stats` showed hit_rate 0.00 after 300 repeats of one
   key. So as configured, the cache does nothing.
2. Root cause: `settings.json` has `"cache_capactiy": 4096` (transposed
   letters) while `kvstore/config.py` looks up `cache_capacity` and falls
   back to 0. Capacity 0 makes `LRUCache.put` a no-op.
3. To check the underlying claim, I corrected the key in my working copy
   and re-measured (script in `measure_lookup.py`, raw output in
   `measure_output.txt`): repeated-key avg dropped from 1.47 ms to
   0.06 ms, hit_rate 0.99. The cache, once actually enabled, helps far
   more than 40% on hot keys.

So: verdict on the shipped configuration is NOT effective (that's what
PERF-VERDICT.md says), the stale benchmark docs should not be trusted as
current, and the one-line settings fix restores (indeed exceeds) the
documented win. I left the fix in the tree for review.
