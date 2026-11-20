"""Assertions for the intent-alternative-ledger evals. Usage:

    check_intent.py <repo>          # eval 6: plain ledger fixture
    check_intent.py <repo> audit    # eval 7: ledger with the audit contract

The branch fixes issue #42 (padded customer names split one customer across
report lines) the long way: a reinvented _clean helper, a
merge_whitespace_duplicates post-pass, and _clean calls at each consumer.

Plain fixture: the boring way is load_orders normalizing `customer` with the
existing text.normalize_space, exactly as it already does for `region` — and
the email padding the branch also handles must be covered by the alternative.

Audit fixture: ledger/audit.py re-emits loaded values byte-for-byte, so
normalizing `customer` at load is wrong. The report must not recommend it
without dealing with the audit contract; the local simplifications (reuse
normalize_space, key the totals on the normalized name so the post-pass goes)
still hold.
"""

import re
import sys

from common import (
    REMOVE_RE,
    blocks,
    blocks_mentioning,
    emit,
    read_report,
    repo_untouched,
    result,
)

INTENT_RE = re.compile(r"\b(intent|goal|purpose|aims? to|trying to)\b", re.I)
PADDING_RE = re.compile(r"\b(whitespace|padd\w*|spaces?|trailing|doubled)\b", re.I)
LOAD_RE = re.compile(r"\b(load_orders|load\.py)\b", re.I)
ACT_RE = re.compile(
    r"\b(normaliz\w*|move\w*|apply\w*|call\w*|use|using|reuse\w*|"
    r"at (the )?(load|ingest\w*|source|boundary))\b",
    re.I,
)
AUDIT_RE = re.compile(r"\b(audit\w*|raw|byte[- ]for[- ]byte|verbatim|reconcil\w*)\b", re.I)
# A block that warns against or rules out load-time normalization.
REJECT_RE = re.compile(
    r"\b(not|never|can'?t|cannot|wrong|break\w*|unsafe|violat\w*|instead)\b", re.I
)


def excerpt(block, limit=160):
    flat = " ".join(block.split())
    return flat[:limit] + ("..." if len(flat) > limit else "")


def closest(found):
    return "; closest block: " + excerpt(found[0]) if found else ""


def main(repo, variant):
    results = []

    ok, evidence = repo_untouched(repo)
    results.append(result("repo_untouched_report_only", ok, evidence))

    report = read_report(repo) or ""
    results.append(result(
        "report_exists",
        len(report) >= 300,
        "report.md has %d chars" % len(report) if report else "report.md missing",
    ))

    intent = next(
        (
            b for b in blocks(report)
            if INTENT_RE.search(b) and PADDING_RE.search(b) and re.search(r"customer", b, re.I)
        ),
        None,
    )
    results.append(result(
        "intent_stated: a block states the change's intent (padded names, customer)",
        intent is not None,
        excerpt(intent) if intent else "no block pairs intent language with padding + customer",
    ))

    clean_blocks = [b for b in blocks_mentioning(report, "_clean") if "normalize_space" in b]
    results.append(result(
        "reinvented_clean_addressed: a block ties _clean to the existing normalize_space",
        bool(clean_blocks),
        excerpt(clean_blocks[0]) if clean_blocks
        else "no block names both _clean and normalize_space"
        + closest(blocks_mentioning(report, "_clean")),
    ))

    merge_blocks = blocks_mentioning(report, "merge_whitespace_duplicates")
    hit = next((b for b in merge_blocks if REMOVE_RE.search(b)), None)
    results.append(result(
        "merge_pass_made_unnecessary: a block recommends deleting the post-pass",
        hit is not None,
        excerpt(hit) if hit else "no merge_whitespace_duplicates block with removal language"
        + closest(merge_blocks),
    ))

    load_blocks = [
        b for b in blocks(report)
        if LOAD_RE.search(b) and "normalize_space" in b and ACT_RE.search(b)
    ]
    if variant == "audit":
        unsafe = [
            b for b in load_blocks
            if re.search(r"customer", b, re.I)
            and not (AUDIT_RE.search(b) and REJECT_RE.search(b))
        ]
        results.append(result(
            "no_unsafe_load_normalization: no block recommends normalizing customer "
            "at load without dealing with the audit contract",
            not unsafe,
            "offending block: " + excerpt(unsafe[0]) if unsafe
            else "%d load-normalization blocks, all address the audit contract"
            % len(load_blocks),
        ))
    else:
        results.append(result(
            "proposes_load_boundary_fix: a block proposes normalizing at load_orders "
            "with normalize_space",
            bool(load_blocks),
            excerpt(load_blocks[0]) if load_blocks
            else "no block pairs load_orders/load.py with normalize_space and an action"
            + closest([b for b in blocks(report) if LOAD_RE.search(b)]),
        ))
        email = [b for b in load_blocks if re.search(r"\bemail", b, re.I)]
        results.append(result(
            "alternative_covers_email: the load-boundary alternative also covers the "
            "padded email the branch handles",
            bool(email),
            excerpt(email[0]) if email else "no load-boundary block mentions email",
        ))

    emit(results)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
