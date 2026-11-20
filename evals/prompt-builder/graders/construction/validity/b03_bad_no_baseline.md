# Task: Diagnose and fix the search API p95 latency regression

You are working alone overnight in the `searchd` repo. No human will be available — do not block waiting for answers. When you hit an ambiguous call, make the best decision, record your assumptions in NOTES.md, and proceed on your own judgment.

## Pre-registration

Before making changes, write down in NOTES.md what you expect to find and what you expect each change to do: the predicted cause of the ~30% p95 latency regression and the expected size of the improvement, so results are judged against a prediction rather than rationalized afterwards.

## Noise discipline

Bench numbers are noisy — ±10% run to run — so always compare medians of five runs and treat any delta inside that band as no change.

## Scope

The public API must not change. Out of scope: dependency upgrades, rewriting the storage layer, or touching anything outside `searchd/`. Only change what the diagnosis implicates.

## Completion gate

The task is not done until `make bench` (median of five runs) shows p95 back at its level from a month ago, and the full test suite passes: run `python -m pytest tests/` and it must exit 0 before you declare the work complete.

## No regressions elsewhere

The fix must not degrade correctness or make any other endpoint slower. Re-run `scripts/loadtest.sh` and confirm no endpoint got worse.

## Adversarial verification

After you believe the fix is complete, spawn a fresh session (a subagent that did not write the changes) and give it one mandate: try to prove the result wrong — attack the benchmark methodology, look for cherry-picked runs, and check the diff for correctness risks. Address its findings before finishing.

## If it does not pan out

If you cannot find the regression or cannot fix it safely, report that plainly in NOTES.md — describe what you checked and what remains open — rather than guessing or shipping a speculative change.
