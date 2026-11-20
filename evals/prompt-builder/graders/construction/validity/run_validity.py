"""Validity harness for the construction grader (DESIGN.md §4).

Runs check_prompt.py over every hand-labeled prompt in this directory
(filenames encode the brief: b<NN>_*.md) and diffs the grader's verdicts
against expected_matrix.json. A file matches only if the grader emits
exactly the expected assertion set with exactly the expected pass/fail
values. Exit 0 iff every file matches.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKER = HERE.parent / "check_prompt.py"
MATRIX = json.loads((HERE / "expected_matrix.json").read_text())


def grade(brief_id, path):
    proc = subprocess.run(
        [sys.executable, str(CHECKER), str(brief_id), str(path)],
        capture_output=True, text=True,
    )
    try:
        results = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise SystemExit("grader crashed on %s:\n%s" % (path.name, proc.stderr))
    return {r["text"]: r["passed"] for r in results}, {r["text"]: r["evidence"] for r in results}


def main():
    matched = 0
    total = 0
    for fn in sorted(MATRIX):
        total += 1
        expected = MATRIX[fn]
        m = re.match(r"b(\d+)_", fn)
        brief_id = int(m.group(1))
        actual, evidence = grade(brief_id, HERE / fn)

        diffs = []
        for name in sorted(set(expected) | set(actual)):
            if name not in actual:
                diffs.append("  MISSING from grader output: %s (expected %s)"
                             % (name, expected[name]))
            elif name not in expected:
                diffs.append("  EXTRA in grader output: %s (got %s)"
                             % (name, actual[name]))
            elif expected[name] != actual[name]:
                diffs.append("  %s: expected %s, got %s | evidence: %s"
                             % (name, expected[name], actual[name],
                                evidence.get(name, "")[:200]))
        if diffs:
            print("MISMATCH %s (brief %d)" % (fn, brief_id))
            print("\n".join(diffs))
        else:
            matched += 1

    print("VALIDITY: %d/%d files exactly matched" % (matched, total))
    sys.exit(0 if matched == total else 1)


if __name__ == "__main__":
    main()
