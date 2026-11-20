"""Leak-lint for the frozen brief texts (DESIGN.md §1, review fix).

Briefs must be pure natural-language user asks: the skill's private vocabulary
and the manifest's taxonomy labels must not appear in any builder-visible brief,
else the harness hands the no-skill arm the skill's concepts (or lets prompts
pass assertions by echoing labels).

Usage: python3 brief_lint.py   (exit 0 = clean; prints per-brief hits)
Run once before freezing; store the clean output in NOTES.md.
"""

import json
import re
import sys
from pathlib import Path

EVALS_JSON = Path(__file__).resolve().parents[1] / "evals.json"

BANNED = [
    r"\boracle\b",
    r"\bpre-?regist",
    r"\badversarial\b",
    r"\bverifier\b",
    r"\bindependent sources?\b",
    r"\bconverg",
    r"\bNO RESULT\b",
    r"\bunattended\b",
    r"\binteractive\b",
    r"\bmaterial claim",
    r"\bevidence (standard|matrix)\b",
    # six profile names as capitalized labels (natural lowercase usage like
    # "build the fix" or "repair" as a verb is fine)
    r"\b(BUILD|OPTIMIZATION|RESEARCH|DECISION|AUTHORING|REPAIR)\b",
]
BANNED_RES = [re.compile(p) for p in BANNED]


def lint_text(label, text):
    hits = []
    for rx in BANNED_RES:
        for m in rx.finditer(text):
            hits.append("%s: %r at %d" % (label, m.group(0), m.start()))
    return hits


def main():
    data = json.loads(EVALS_JSON.read_text())
    all_hits = []
    for b in data["tracks"]["construction"]["briefs"]:
        all_hits += lint_text("construction/%s" % b["slug"], b["brief"])
    for f in data["tracks"]["rigor"]["fixtures"]:
        all_hits += lint_text("rigor/%s" % f["slug"], f["brief"])
    if all_hits:
        print("\n".join(all_hits))
        print("LINT: %d leak(s)" % len(all_hits))
        sys.exit(1)
    print("LINT: clean (%d construction briefs, %d rigor briefs)" % (
        len(data["tracks"]["construction"]["briefs"]),
        len(data["tracks"]["rigor"]["fixtures"])))


if __name__ == "__main__":
    main()
