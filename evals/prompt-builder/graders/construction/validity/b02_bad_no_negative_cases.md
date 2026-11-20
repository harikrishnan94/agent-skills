# Task: Add a `--json` output flag to `licheck`

Add a `--json` flag to the internal `licheck` CLI (single-file Python, argparse). Machine-readable output must mirror what the human-readable mode prints: same findings, same ordering, same totals.

## Interaction

I am at my desk while you work — if the JSON shape is debatable (key naming, nesting, how to encode severities), ask me before committing to one.

## Pre-registration

Before starting, write down the exact JSON schema you expect to emit and one sample document. Compare the final output against that note and flag any drift.

## Scope

Only change `licheck.py` and its tests. Do not modify the human-readable output path, and leave the exit-code behavior untouched.

## Tests

Add tests asserting that the JSON mode reports the same findings, ordering, and totals as the human-readable mode on the same inputs, and that the output parses as valid JSON.

## Completion gate

The flag is not done until `python -m unittest` passes with zero failures on the full suite.

## Independent check

When you believe it is complete, have a fresh session that did not write the code review the diff, with instructions to prove the JSON mode diverges from the human-readable mode somewhere.

## Honest outcome

If you cannot mirror some part of the human output cleanly in JSON, say so and show me the discrepancy rather than fudging the representation.
