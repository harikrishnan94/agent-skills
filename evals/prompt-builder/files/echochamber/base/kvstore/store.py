"""Backing store: line-scans a JSONL records file on every lookup."""

import json


class KVStore:
    def __init__(self, path):
        self.path = path

    def lookup(self, key):
        needle = '"%s"' % key
        with open(self.path) as fh:
            for line in fh:
                if needle not in line:
                    continue
                record = json.loads(line)
                if record.get("key") == key:
                    return record.get("value")
        return None

    def count(self):
        with open(self.path) as fh:
            return sum(1 for line in fh if line.strip())
