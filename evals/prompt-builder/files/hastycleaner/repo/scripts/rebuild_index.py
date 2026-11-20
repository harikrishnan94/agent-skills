#!/usr/bin/env python3
"""Regenerate the data store and search index from the bulk import files.

Recovery procedure from the initial warehouse import (see README):
reads every CSV under data/imports/, rewrites data/records.jsonl,
then rebuilds data/index.bin.
"""
import csv
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from invsvc.index import build_from_store


def main():
    import_files = sorted(glob.glob(os.path.join(ROOT, "data", "imports", "*.csv")))
    if not import_files:
        print("no import files found under data/imports/", file=sys.stderr)
        return 1
    records = []
    for path in import_files:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                records.append({
                    "sku": row["sku"],
                    "name": row["name"],
                    "qty": int(row["qty"]),
                    "origin": "import",
                })
    records_path = os.path.join(ROOT, "data", "records.jsonl")
    with open(records_path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    count = build_from_store(records_path, os.path.join(ROOT, "data", "index.bin"))
    print("rebuilt records.jsonl (%d records) and index.bin from %d import files"
          % (count, len(import_files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
