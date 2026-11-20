#!/usr/bin/env python3
"""Benchmark report generator for the kvstore lookup benchmark."""

import json
import sys


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "bench/results.json"
    with open(path) as fh:
        r = json.load(fh)
    print("== %s benchmark ==" % r["benchmark"])
    print("dataset:        %s" % r["dataset"])
    print("iterations:     %d lookups over %d keys" % (r["iterations"], r["keys_sampled"]))
    print("uncached avg:   %.2f ms" % r["uncached_avg_ms"])
    print("cached avg:     %.2f ms" % r["cached_avg_ms"])
    print("improvement:    %.0f%%" % r["improvement_pct"])
    print("cache hit rate: %.2f" % r["cache_hit_rate"])


if __name__ == "__main__":
    main()
