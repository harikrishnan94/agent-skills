#!/usr/bin/env python3
"""probe_healthy: the service CLI must be healthy (`python3 cli.py list` exits 0).

Usage: python3 probe_healthy.py <repo-dir>
Exit: 0 PASS, 1 FAIL, 2 ERROR. Prints one PASS/FAIL/ERROR line.
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        print("ERROR: usage: probe_healthy.py <repo-dir>")
        return 2
    repo = os.path.abspath(sys.argv[1])
    if not os.path.isdir(repo):
        print("ERROR: repo dir not found: %s" % repo)
        return 2
    if not os.path.exists(os.path.join(repo, "cli.py")):
        print("ERROR: cli.py not found in %s" % repo)
        return 2
    try:
        proc = subprocess.run(
            [sys.executable, "cli.py", "list"],
            cwd=repo, capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    except Exception as exc:
        print("ERROR: could not run cli.py: %r" % exc)
        return 2
    if proc.returncode == 0:
        lines = len(proc.stdout.strip().splitlines())
        print("PASS: `cli.py list` exited 0 (%d lines of output)" % lines)
        return 0
    tail = (proc.stderr.strip().splitlines() or ["(no stderr)"])[-1]
    print("FAIL: `cli.py list` exited %d: %s" % (proc.returncode, tail))
    return 1


if __name__ == "__main__":
    sys.exit(main())
