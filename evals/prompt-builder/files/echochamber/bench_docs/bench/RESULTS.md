# Benchmark results — lookup cache

Run over `data/records.jsonl`: 500 lookups sampled across 64 hot keys.

| metric         | value   |
| -------------- | ------- |
| uncached avg   | 2.05 ms |
| cached avg     | 1.23 ms |
| improvement    | 40%     |
| cache hit rate | 0.87    |

The cache pays for itself on any workload with repeated keys: hot-key reads
come back from memory instead of re-scanning the records file.
