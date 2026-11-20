"""Read and write the v2 on-disk store format.

A v2 store file is JSON lines: a header record on the first line, then one
record object per line.
"""
import json

HEADER = {"format": "docstore", "version": 2}


def read_records(path):
    """Read a v2 store file and return its records as a dict."""
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines:
        raise ValueError("empty store file: %s" % path)
    header = json.loads(lines[0])
    if header.get("format") != "docstore" or header.get("version") != 2:
        raise ValueError("not a v2 store file: %s" % path)
    records = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        rec = json.loads(line)
        if not isinstance(rec, dict) or set(rec) != {"key", "value"}:
            raise ValueError("not a v2 store file: %s" % path)
        records[rec["key"]] = rec["value"]
    return records


def write_records(path, records):
    """Write records to a v2 store file."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(HEADER) + "\n")
        for key in sorted(records):
            fh.write(json.dumps({"key": key, "value": records[key]}) + "\n")
