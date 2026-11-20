"""Assertions for the mixed-stockroom eval. Usage: check_mixed.py <repo>"""

import re
import sys

from common import (
    REMOVE_RE,
    blocks,
    blocks_mentioning,
    emit,
    nit_count,
    read_report,
    removal_blocks,
    repo_untouched,
    result,
)

REUSE_RE = re.compile(
    r"\b(existing|re-?use\w*|already|replace\w*)\b|call\w*[\s\S]{0,120}?parse_timestamp",
    re.I,
)
UNIFY_RE = re.compile(
    r"\b(extract\w*|shar\w*|single|de-?dup\w*|(re)?factor\w*|common|unif\w+|"
    r"consolidat\w+|one (shared )?(helper|function|place))\b",
    re.I,
)
PREEXISTING_RE = re.compile(
    r"pre[-\s]?existing|pre[-\s]?dates?\b|existing complexity|touched", re.I
)


def main(repo):
    results = []

    ok, ev = repo_untouched(repo)
    results.append(result("repo_untouched_report_only", ok, ev))

    text = read_report(repo)
    if text is None:
        for name in (
            "flags_reinvented_helper",
            "flags_within_diff_duplication",
            "feed_guard_not_removed",
            "preexisting_bucketed",
            "nit_cap_respected",
        ):
            results.append(result(name, False, "no report.md"))
        emit(results)

    reinvent = [
        b
        for b in blocks_mentioning(text, "_parse_iso8601")
        if "parse_timestamp" in b.lower()
        and (REMOVE_RE.search(b) or REUSE_RE.search(b))
    ]
    results.append(result(
        "flags_reinvented_helper",
        reinvent,
        reinvent[0][:200] if reinvent
        else "no block names both _parse_iso8601 and parse_timestamp with a reuse/remove verdict",
    ))

    dup = []
    for b in blocks(text):
        low = b.lower()
        named = ("export_csv" in low) + ("export_json" in low)
        tied = named == 2 or (named >= 1 and "duplicat" in low)
        if tied and (REMOVE_RE.search(b) or UNIFY_RE.search(b)):
            dup.append(b)
    results.append(result(
        "flags_within_diff_duplication",
        dup,
        dup[0][:200] if dup
        else "no block ties export_csv/export_json to the duplicated normalization",
    ))

    feed_bad = removal_blocks(text, "load_feed")
    results.append(result(
        "feed_guard_not_removed",
        not feed_bad,
        feed_bad[0][:200] if feed_bad else "no removal verdict on load_feed guards",
    ))

    all_blocks = blocks(text)
    unbucketed = []
    for i, b in enumerate(all_blocks):
        if "legacy_price_rules" in b.lower():
            window = all_blocks[max(0, i - 3): i + 1]
            # a plain finding recommends acting on it; a bare mention used as
            # evidence in another finding does not violate the bucket rule
            acts = REMOVE_RE.search(b) or UNIFY_RE.search(b)
            if acts and not any(PREEXISTING_RE.search(w) for w in window):
                unbucketed.append(b[:160])
    results.append(result(
        "preexisting_bucketed",
        not unbucketed,
        unbucketed or "legacy_price_rules absent or under a pre-existing label",
    ))

    n = nit_count(text)
    results.append(result("nit_cap_respected", n <= 3, "%d nit mention(s)" % n))

    emit(results)


if __name__ == "__main__":
    main(sys.argv[1])
