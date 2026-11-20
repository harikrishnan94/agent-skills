"""Bait-leak audit for rigor-track generated prompts (DESIGN.md §3).

Usage: python3 audit_leaks.py <fixture-slug> <generated_prompt.md>

Loads files/<slug>/grader/leak_terms.txt (one Python regex per line, case-
insensitive) and the optional leak_exempt.txt (same format). The prompt text
is reflowed (hard-wrapped lines within a paragraph joined) before matching —
multi-word patterns must not be defeated by line wrapping. A match is
EXEMPT if any exempt pattern also matches the same sentence (e.g. thinwell's
conditional honesty phrasing: "IF the reason cannot be determined, say so"
states a condition, not the fixture's ground truth).

Exit 0 = CLEAN, 1 = LEAKED (matches printed), 2 = usage/IO error.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def reflow(text):
    """Join hard-wrapped lines inside paragraphs; keep paragraph breaks."""
    paras = re.split(r"\n\s*\n", text)
    return "\n\n".join(re.sub(r"\s*\n\s*", " ", p).strip() for p in paras)


def sentences(text):
    return re.split(r"(?<=[.!?])\s+|\n\n", text)


def load_patterns(path):
    if not path.exists():
        return []
    pats = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pats.append(re.compile(line, re.I))
    return pats


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    slug, prompt_path = sys.argv[1], Path(sys.argv[2])
    gdir = ROOT / "files" / slug / "grader"
    terms = load_patterns(gdir / "leak_terms.txt")
    exempts = load_patterns(gdir / "leak_exempt.txt")
    if not terms:
        print("ERROR: no leak terms for %s" % slug)
        sys.exit(2)
    text = reflow(prompt_path.read_text(encoding="utf-8"))

    hits = []
    for sent in sentences(text):
        for rx in terms:
            m = rx.search(sent)
            if not m:
                continue
            if any(e.search(sent) for e in exempts):
                continue
            hits.append((rx.pattern[:60], m.group(0)[:80], sent.strip()[:160]))
    if hits:
        for pat, match, sent in hits:
            print("LEAKED  pattern=%r  match=%r\n        in: %s" % (pat, match, sent))
        print("RESULT: LEAKED (%d hits)" % len(hits))
        sys.exit(1)
    print("RESULT: CLEAN")
    sys.exit(0)


if __name__ == "__main__":
    main()
