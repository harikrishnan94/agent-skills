"""Shared helpers for the humanize eval checkers.

Each check_*.py prints a JSON array of {"text", "passed", "evidence"} objects
(the grading.json expectations format) for one eval's assertions.
"""

import json
import re
import subprocess
import sys

EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),
    (0x2600, 0x27BF),
    (0x2B00, 0x2BFF),
    (0xFE00, 0xFE0F),
)


def find_emoji(text):
    hits = []
    for ch in text:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in EMOJI_RANGES):
            hits.append("U+%04X %s" % (cp, ch))
    return hits


def git(repo, *args):
    p = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True
    )
    return p.returncode, p.stdout, p.stderr


def run_tests(repo):
    p = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return p.returncode, (p.stdout + p.stderr)[-2000:]


def added_lines(repo, base, paths=None):
    """Added ('+') lines of the diff from base to the working tree."""
    args = ["diff", base, "--"] + (paths or [])
    _, out, _ = git(repo, *args)
    return [
        line[1:]
        for line in out.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def new_commit_messages(repo, base):
    """(subject, body) per commit added since base."""
    _, out, _ = git(repo, "log", "--format=%H", base + "..HEAD")
    msgs = []
    for sha in out.split():
        _, subj, _ = git(repo, "log", "-1", "--format=%s", sha)
        _, body, _ = git(repo, "log", "-1", "--format=%b", sha)
        msgs.append((subj.strip("\n"), body))
    return msgs


BULLET_RE = re.compile(r"^\s*[-*•] ", re.M)
HEADER_RE = re.compile(r"^#{1,6} ", re.M)


def result(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def emit(results):
    json.dump(results, sys.stdout, indent=1)
    print()
    sys.exit(0 if all(r["passed"] for r in results) else 1)
