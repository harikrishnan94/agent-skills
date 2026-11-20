"""Assertions for the seeded-accretion-logship eval. Usage: check_seeded.py <repo>

Positive detections use REMOVE_RE.search directly rather than
recommends_removal/removal_blocks: those veto on keep-words, which legitimate
findings often contain incidentally ("keep the JSON arm, delete the flag").
"""

import re
import sys

from common import (
    REMOVE_RE,
    blocks_mentioning,
    emit,
    read_report,
    repo_untouched,
    result,
)

HISTORY_RE = re.compile(
    r"\b(commit\w*|introduc\w*|later|orphan\w*|earlier|history|branch\w*)\b", re.I
)
UNIFY_RE = re.compile(r"\b(unif\w+|merg\w+|fold\w*)\b|single shape", re.I)


def excerpt(block, limit=160):
    flat = " ".join(block.split())
    return flat[:limit] + ("..." if len(flat) > limit else "")


def closest(blocks):
    return "; closest block: " + excerpt(blocks[0]) if blocks else ""


def main(repo):
    results = []

    ok, evidence = repo_untouched(repo)
    results.append(result("repo_untouched_report_only", ok, evidence))

    report = read_report(repo)
    results.append(result(
        "report_exists_with_findings",
        report is not None and len(report) >= 300,
        "report.md missing" if report is None
        else "report.md has %d chars" % len(report),
    ))
    report = report or ""

    legacy_blocks = [
        b
        for b in blocks_mentioning(report, "legacy")
        if "records.py" in b.lower() or "format_entry" in b.lower()
    ]
    hit = next((b for b in legacy_blocks if REMOVE_RE.search(b)), None)
    results.append(result(
        "flags_constant_threaded_flag",
        hit is not None,
        excerpt(hit) if hit
        else "no block names legacy with records.py/format_entry and recommends "
        "removal" + closest(legacy_blocks),
    ))

    chunk_blocks = blocks_mentioning(report, "_chunk")
    hit = next(
        (b for b in chunk_blocks if REMOVE_RE.search(b) and HISTORY_RE.search(b)),
        None,
    )
    results.append(result(
        "flags_dead_scaffolding_with_history",
        hit is not None,
        excerpt(hit) if hit
        else "no _chunk block pairs removal with history evidence"
        + closest(chunk_blocks),
    ))

    adapter_blocks = blocks_mentioning(report, "batch_to_rows") or [
        b
        for b in blocks_mentioning(report, "BatchWriter")
        if re.search(r"\bBatch\b", b)
    ]
    hit = next(
        (b for b in adapter_blocks if REMOVE_RE.search(b) or UNIFY_RE.search(b)),
        None,
    )
    results.append(result(
        "flags_adapter_between_own_shapes",
        hit is not None,
        excerpt(hit) if hit
        else "no batch_to_rows (or Batch+BatchWriter) block recommends "
        "removal or unification" + closest(adapter_blocks),
    ))

    emit(results)


if __name__ == "__main__":
    main(sys.argv[1])
