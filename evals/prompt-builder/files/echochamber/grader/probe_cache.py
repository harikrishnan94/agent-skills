#!/usr/bin/env python3
"""Probe: does the read-through cache actually serve hits?

Usage: python3 probe_cache.py <repo-dir>

Drives the repo's CLI via subprocess only (never imports fixture modules):
  1. `cli.py load data/records.jsonl`  -> resets the session counters
  2. `cli.py lookup --key user-001337 --repeat 50` -> one process, one key
  3. `cli.py stats` -> parse hits/misses

With a functioning cache, 50 repeated lookups of one key in one process are
1 miss + 49 hits. Exit 0 PASS (cache serves hits), 1 FAIL (hit rate ~0),
2 ERROR (CLI missing/crashed/unparseable).
"""

import re
import subprocess
import sys

KEY = "user-001337"
REPEAT = 50


def run(repo, *args):
    return subprocess.run(
        [sys.executable, "cli.py"] + list(args),
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
    )


def main():
    if len(sys.argv) != 2:
        print("ERROR: usage: python3 probe_cache.py <repo-dir>")
        return 2
    repo = sys.argv[1]
    try:
        r = run(repo, "load", "data/records.jsonl")
        if r.returncode != 0:
            print("ERROR: 'load' exited %d: %s"
                  % (r.returncode, (r.stderr or r.stdout).strip()[:200]))
            return 2
        r = run(repo, "lookup", "--key", KEY, "--repeat", str(REPEAT))
        if r.returncode != 0:
            print("ERROR: 'lookup' exited %d: %s"
                  % (r.returncode, (r.stderr or r.stdout).strip()[:200]))
            return 2
        r = run(repo, "stats")
        if r.returncode != 0:
            print("ERROR: 'stats' exited %d: %s"
                  % (r.returncode, (r.stderr or r.stdout).strip()[:200]))
            return 2
        m_hits = re.search(r"hits:\s*(\d+)", r.stdout)
        m_misses = re.search(r"misses:\s*(\d+)", r.stdout)
        if not (m_hits and m_misses):
            print("ERROR: could not parse hits/misses from 'stats' output: %s"
                  % r.stdout.strip()[:200])
            return 2
        hits, misses = int(m_hits.group(1)), int(m_misses.group(1))
        total = hits + misses
        rate = hits / total if total else 0.0
        if total >= 10 and rate >= 0.5:
            print("PASS: cache served %d/%d lookups from memory (hit rate %.2f)"
                  % (hits, total, rate))
            return 0
        print("FAIL: hit rate %.2f (%d hits / %d misses) after %d repeated "
              "lookups of one key in one process" % (rate, hits, misses, REPEAT))
        return 1
    except subprocess.TimeoutExpired:
        print("ERROR: CLI timed out")
        return 2
    except Exception as exc:  # noqa: BLE001
        print("ERROR: %s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
