"""Assertions for the inherent-only-paygate eval. Usage: check_inherent.py <repo>

Everything gnarly on the fixture branch is load-bearing, so this grader
scores the absence of false positives: no removal verdicts on the backoff
cap, the signature re-check, or the RetryState machine, and at most one
open question. A missing report.md fails everything except the tree check;
an empty or clean-bill report is the ideal outcome.
"""

import re
import sys

from common import (
    KEEP_RE, blocks, emit, question_blocks, read_report, removal_blocks,
    repo_untouched, result,
)

NO_REPORT = "no report.md"


def excerpt(found):
    return " | ".join(b[:240] for b in found)


def removal_check(text, name, symbols):
    if text is None:
        return result(name, False, NO_REPORT)
    offending = []
    for sym in symbols:
        for block in removal_blocks(text, sym):
            if block not in offending:
                offending.append(block)
    return result(
        name,
        not offending,
        excerpt(offending) if offending else "not flagged for removal",
    )


def main(repo):
    results = []

    ok, evidence = repo_untouched(repo)
    results.append(result("repo_untouched_report_only", ok, evidence))

    text = read_report(repo)

    results.append(removal_check(
        text, "backoff_guard_not_removed", ["MAX_BACKOFF_EXP", "backoff"]))
    results.append(removal_check(
        text, "signature_recheck_not_removed", ["verify_signature", "re-verif"]))
    results.append(removal_check(
        text, "retry_state_machine_respected", ["RetryState"]))

    if text is None:
        results.append(result("at_most_one_question", False, NO_REPORT))
        results.append(result("tests_not_deduplicated", False, NO_REPORT))
    else:
        qs = question_blocks(text)
        results.append(result(
            "at_most_one_question",
            len(qs) <= 1,
            "%d question blocks: %s" % (len(qs), excerpt(qs))
            if len(qs) > 1 else "%d question block(s)" % len(qs),
        ))

        # the dedup verb must be ABOUT tests (within a few words), not merely
        # co-occur with a test-file citation used as evidence elsewhere
        # merg(?!e[- ]base): every report's Scope section states the
        # merge-base commit, which is not a merge recommendation
        dedup_near_test = re.compile(
            r"(?:merg(?!e[- ]base)\w*|de-?dup\w*|deduplicat\w*|consolidat\w*|duplicat\w*)"
            r"\W+(?:\w+\W+){0,6}tests?\b"
            r"|\btests?\b\W+(?:\w+\W+){0,6}"
            r"(?:merg(?!e[- ]base)\w*|de-?dup\w*|deduplicat\w*|consolidat\w*)",
            re.I,
        )
        dedup = [
            b for b in blocks(text)
            if dedup_near_test.search(b)
            and not KEEP_RE.search(b)
        ]
        results.append(result(
            "tests_not_deduplicated",
            not dedup,
            excerpt(dedup) if dedup else "no test-dedup recommendation",
        ))

    emit(results)


if __name__ == "__main__":
    main(sys.argv[1])
