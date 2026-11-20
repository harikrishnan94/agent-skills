"""Grade the apply-default-logship eval: an imperative invocation must apply
the proven-safe simplifications to the working tree (uncommitted), leave the
suite green, and report each applied edit with a receipt.

The two plants that must actually be fixed in the tree are the ones that
clear Step 7's gate cleanly: the constant-threaded legacy flag (restructure
with complete caller enumeration + direct test coverage) and the orphaned
_chunk helper (production-dead deletion on liveness receipts). The
Batch/batch_to_rows adapter is a multi-file restructure the skill may apply
or demote; it only has to be addressed in the report.
"""

import re
import subprocess
import sys
from pathlib import Path

from common import blocks_mentioning, emit, git, read_report, result

ALLOWED_PATHS = {
    "logship/records.py",
    "logship/exporter.py",
    "logship/batch.py",
    "logship/writer.py",
    "logship/cli.py",
    "tests/test_export.py",
    "report.md",
}


def main(repo):
    results = []
    report = read_report(repo)

    _, head, _ = git(repo, "rev-parse", "HEAD")
    _, tag, _ = git(repo, "rev-parse", "fixture-head^{commit}")
    _, status, _ = git(repo, "status", "--porcelain")
    changed = [
        line[3:].strip() for line in status.splitlines() if line.strip()
    ]
    code_changes = [p for p in changed if p != "report.md"]

    results.append(result(
        "edits_uncommitted_head_unchanged: HEAD still at fixture-head and at "
        "least one code file modified in the working tree",
        head.strip() == tag.strip() and bool(code_changes),
        "HEAD %s vs fixture-head %s; code changes: %r"
        % (head.strip()[:8], tag.strip()[:8], code_changes),
    ))

    records = (Path(repo) / "logship" / "records.py").read_text()
    tree_py = "".join(
        p.read_text() for p in sorted(Path(repo).glob("logship/*.py"))
    ) + (Path(repo) / "tests" / "test_export.py").read_text()
    results.append(result(
        "legacy_flag_removed_from_tree: the legacy parameter and its dead arm "
        "are gone from records.py and no caller passes legacy=",
        "legacy" not in records and "legacy=" not in tree_py,
        "records.py has 'legacy': %s; tree has 'legacy=': %s"
        % ("legacy" in records, "legacy=" in tree_py),
    ))

    exporter = (Path(repo) / "logship" / "exporter.py").read_text()
    results.append(result(
        "dead_chunk_deleted: the orphaned _chunk helper is gone from "
        "exporter.py",
        "_chunk" not in exporter,
        "'_chunk' in exporter.py: %s" % ("_chunk" in exporter),
    ))

    suite = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=repo, capture_output=True, text=True,
    )
    results.append(result(
        "suite_green_after_edits: python -m unittest passes on the edited tree",
        suite.returncode == 0,
        (suite.stderr or suite.stdout).strip().splitlines()[-1]
        if (suite.stderr or suite.stdout).strip() else "no output",
    ))

    has_receipt = bool(report) and bool(
        re.search(r"\bstatus\b[^\n]{0,60}\bapplied\b", report, re.I)
    ) and bool(re.search(r"\b(unittest|pytest|test suite|tests? pass)", report, re.I))
    results.append(result(
        "report_status_applied_with_receipt: report.md marks applied findings "
        "with a Status line and a verification receipt",
        has_receipt,
        "report exists: %s; status+receipt found: %s" % (bool(report), has_receipt),
    ))

    results.append(result(
        "adapter_addressed: report mentions batch_to_rows (applied or "
        "report-only — either is acceptable)",
        bool(report) and bool(blocks_mentioning(report, "batch_to_rows")),
        "blocks mentioning batch_to_rows: %d"
        % (len(blocks_mentioning(report, "batch_to_rows")) if report else 0),
    ))

    unexpected = [p for p in changed if p not in ALLOWED_PATHS]
    results.append(result(
        "only_expected_files_touched: every modified path is one the plants "
        "or their fixes can legitimately reach",
        not unexpected,
        "unexpected paths: %r" % unexpected,
    ))

    emit(results)


if __name__ == "__main__":
    main(sys.argv[1])
