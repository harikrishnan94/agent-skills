#!/usr/bin/env python3
"""Migrate a legacy v1 store file to the current on-disk format.

Usage: python3 migrate.py OLD.v1 NEW.store
"""
import json
import sys

from store import v2

# converts v1 files to the v2 format introduced during the 1.x cleanup


def read_v1(path):
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    records = {}
    for line in lines:
        if not line.strip():
            continue
        rec = json.loads(line)
        if not isinstance(rec, dict) or set(rec) != {"key", "value"}:
            raise ValueError("not a v1 store file: %s" % path)
        records[rec["key"]] = rec["value"]
    return records


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    records = read_v1(argv[0])
    v2.write_records(argv[1], records)
    print("migrated %d records" % len(records))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
