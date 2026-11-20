#!/usr/bin/env python3
"""Command-line interface for the kvstore lookup service."""

import argparse
import json
import os
import sys
import time

from kvstore.cache import LRUCache
from kvstore.store import KVStore

CACHE_CAPACITY = 4096
DATA_PATH = "data/records.jsonl"

STATS_PATH = ".kvstats.json"


def _read_stats():
    if os.path.exists(STATS_PATH):
        with open(STATS_PATH) as fh:
            return json.load(fh)
    return {"hits": 0, "misses": 0}


def _write_stats(stats):
    with open(STATS_PATH, "w") as fh:
        json.dump(stats, fh)


def cmd_load(args):
    store = KVStore(args.data)
    count = store.count()
    _write_stats({"hits": 0, "misses": 0})
    print("loaded %d records from %s" % (count, args.data))
    return 0


def cmd_lookup(args):
    store = KVStore(args.data or DATA_PATH)
    cache = LRUCache(CACHE_CAPACITY)
    value = None
    start = time.perf_counter()
    for _ in range(args.repeat):
        value = cache.get(args.key)
        if value is None:
            value = store.lookup(args.key)
            if value is not None:
                cache.put(args.key, value)
    elapsed = time.perf_counter() - start
    stats = _read_stats()
    stats["hits"] += cache.hits
    stats["misses"] += cache.misses
    _write_stats(stats)
    if value is None:
        print("key not found: %s" % args.key, file=sys.stderr)
        return 1
    print(json.dumps(value, sort_keys=True))
    if args.repeat > 1:
        print("avg_ms: %.3f" % (elapsed / args.repeat * 1000))
    return 0


def cmd_stats(args):
    stats = _read_stats()
    total = stats["hits"] + stats["misses"]
    rate = stats["hits"] / total if total else 0.0
    print("hits: %d" % stats["hits"])
    print("misses: %d" % stats["misses"])
    print("hit_rate: %.2f" % rate)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="kvstore",
        description="Key-value lookup service with a read-through cache.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_load = sub.add_parser("load", help="validate a records file and reset session counters")
    p_load.add_argument("data", help="path to a records .jsonl file")
    p_load.set_defaults(func=cmd_load)

    p_lookup = sub.add_parser("lookup", help="look up a key (read-through cache)")
    p_lookup.add_argument("--key", required=True, help="record key to look up")
    p_lookup.add_argument("--repeat", type=int, default=1,
                          help="repeat the lookup N times (prints avg_ms)")
    p_lookup.add_argument("--data", help="override the records file")
    p_lookup.set_defaults(func=cmd_lookup)

    p_stats = sub.add_parser("stats", help="show cumulative cache hit/miss counters")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
