"""Shared helpers for the reduce-complexity eval checkers.

Each check_*.py prints a JSON array of {"text", "passed", "evidence"} objects
(the grading.json expectations format) for one eval's assertions. Unlike the
humanize graders, these score the report text the run wrote to report.md; the
fixture repo itself must be untouched, because reduce-complexity is
report-only.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def git(repo, *args):
    p = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True
    )
    return p.returncode, p.stdout, p.stderr


def read_report(repo):
    path = Path(repo) / "report.md"
    return path.read_text(encoding="utf-8") if path.exists() else None


def blocks(text):
    """Blank-line-separated chunks; one finding's fields stay together.

    A chunk that is only a markdown heading is merged into the following
    chunk: the skill's clean-report narrative puts the verdict-bearing
    heading ("### Strongest candidate: ...") in its own block, and judging
    the paragraph without it misreads candidate descriptions as findings.
    """
    raw = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    merged = []
    for b in raw:
        if merged and re.fullmatch(r"#{1,6}\s+[^\n]*", merged[-1]):
            merged[-1] = merged[-1] + "\n" + b
        else:
            merged.append(b)
    return merged


def blocks_mentioning(text, symbol):
    return [b for b in blocks(text) if symbol.lower() in b.lower()]


REMOVE_RE = re.compile(
    r"\b(remove|removing|removed|delete|deleting|drop|dropping|strip|"
    r"eliminate|inline|inlining|collapse|unnecessary|redundant|"
    r"dead(?![ -](letter|guard|state))|useless|pointless|simplif\w+ away)\b",
    re.I,
)
KEEP_RE = re.compile(
    r"\b(keep|retain|preserve|inherent|justified|intentional|deliberate|"
    r"mandated|requested|require\w*|accepted|killed|suppress\w*|candidates?|"
    r"defen[cs]e[- ]in[- ]depth|label|ask|"
    r"question|leave|load[- ]bearing|belt[- ]and[- ]suspenders|"
    r"not (be )?(removed|removable)|do(es)? not|don'?t|must stay|"
    r"should stay|trust boundar\w+)\b",
    re.I,
)


def recommends_removal(block):
    """A block reads as a removal recommendation with no keep/ask verdict."""
    return bool(REMOVE_RE.search(block)) and not KEEP_RE.search(block)


def removal_blocks(text, symbol):
    return [b for b in blocks_mentioning(text, symbol) if recommends_removal(b)]


def repo_untouched(repo, head_tag="fixture-head"):
    """(ok, evidence): HEAD still at the fixture tag, tree clean bar report.md."""
    _, head, _ = git(repo, "rev-parse", "HEAD")
    _, tag, _ = git(repo, "rev-parse", head_tag + "^{commit}")
    _, status, _ = git(repo, "status", "--porcelain")
    extras = [
        line
        for line in status.splitlines()
        if line.strip() and not line.endswith("report.md")
    ]
    ok = head.strip() == tag.strip() and not extras
    return ok, "HEAD %s vs %s %s; status extras: %r" % (
        head.strip()[:8], head_tag, tag.strip()[:8], extras,
    )


QUESTION_ITEM_RES = (
    re.compile(r"(severity|disposition)[^\n]*question", re.I),
    re.compile(
        r"(^|\n)\s*(?:[-*\d]+[.)]?\s*)?(?:\*\*|#+\s*)?questions? for the author\b",
        re.I,
    ),
    re.compile(r"ask the author\s*[:—–-]", re.I),
)


def question_blocks(text):
    """Blocks that ARE question items — a question verdict in the severity/
    disposition field or an explicit question-for-the-author label — not
    narrative mentions of a question elsewhere in the report."""
    return [b for b in blocks(text) if any(p.search(b) for p in QUESTION_ITEM_RES)]


def nit_count(text):
    """Findings marked nit-severity ('nit' singular; summary lines say 'nits')."""
    return len(re.findall(r"\bnit\b", text, re.I))


def result(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def emit(results):
    json.dump(results, sys.stdout, indent=1)
    print()
    sys.exit(0 if all(r["passed"] for r in results) else 1)
