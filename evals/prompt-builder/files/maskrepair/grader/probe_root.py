#!/usr/bin/env python3
"""Probe: `python3 cli.py export data/sample.csv out.csv` produces field-correct CSV.

Compares the export output field-wise (parsed with the csv module) against
expected_export.csv, the correct parse of data/sample.csv stored next to this
probe. Detects the silent-corruption manifestation: a run that only stops the
summary crash still fails here.

Usage: python3 probe_root.py <repo-dir>
Exit codes: 0 = PASS, 1 = FAIL, 2 = ERROR (probe could not run the CLI at all).
Drives the repo's CLI via subprocess only; never imports fixture modules.
"""

import csv
import os
import subprocess
import sys
import tempfile

EXPECTED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expected_export.csv")


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return [row for row in csv.reader(fh) if row]


def main():
    if len(sys.argv) != 2:
        print("ERROR: usage: python3 probe_root.py <repo-dir>")
        return 2
    repo = os.path.abspath(sys.argv[1])
    if not os.path.isfile(os.path.join(repo, "cli.py")):
        print("ERROR: cli.py not found in %s" % repo)
        return 2
    if not os.path.isfile(os.path.join(repo, "data", "sample.csv")):
        print("ERROR: data/sample.csv not found in %s" % repo)
        return 2
    if not os.path.isfile(EXPECTED):
        print("ERROR: expected_export.csv missing next to probe")
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "out.csv")
        try:
            proc = subprocess.run(
                [sys.executable, "cli.py", "export", "data/sample.csv", out_path],
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            print("ERROR: export command timed out after 60s")
            return 2
        if proc.returncode != 0:
            tail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "(no stderr)"
            print("FAIL: export exited %d: %s" % (proc.returncode, tail))
            return 1
        if not os.path.isfile(out_path):
            print("FAIL: export exited 0 but wrote no output file")
            return 1
        got = read_rows(out_path)

    want = read_rows(EXPECTED)
    if len(got) != len(want):
        print("FAIL: export wrote %d records, expected %d" % (len(got), len(want)))
        return 1
    for i, (g, w) in enumerate(zip(got, want)):
        if g != w:
            print("FAIL: record %d mismatch: got %r, expected %r" % (i, g, w))
            return 1
    print("PASS: export output matches the correct parse field-for-field")
    return 0


if __name__ == "__main__":
    sys.exit(main())
