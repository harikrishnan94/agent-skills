#!/usr/bin/env python3
"""Probe: `python3 cli.py summary data/sample.csv` completes and prints a summary.

Usage: python3 probe_crash.py <repo-dir>
Exit codes: 0 = PASS, 1 = FAIL, 2 = ERROR (probe could not run the CLI at all).
Drives the repo's CLI via subprocess only; never imports fixture modules.
"""

import os
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        print("ERROR: usage: python3 probe_crash.py <repo-dir>")
        return 2
    repo = os.path.abspath(sys.argv[1])
    if not os.path.isfile(os.path.join(repo, "cli.py")):
        print("ERROR: cli.py not found in %s" % repo)
        return 2
    if not os.path.isfile(os.path.join(repo, "data", "sample.csv")):
        print("ERROR: data/sample.csv not found in %s" % repo)
        return 2
    try:
        proc = subprocess.run(
            [sys.executable, "cli.py", "summary", "data/sample.csv"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print("ERROR: summary command timed out after 60s")
        return 2
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "(no stderr)"
        print("FAIL: summary exited %d: %s" % (proc.returncode, tail))
        return 1
    if not any(ch.isdigit() for ch in proc.stdout):
        print("FAIL: summary exited 0 but printed no figures")
        return 1
    print("PASS: summary exited 0 and printed a summary")
    return 0


if __name__ == "__main__":
    sys.exit(main())
