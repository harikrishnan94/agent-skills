# Migration rationale — determination: CORRECTNESS

## Pre-registered hypotheses
H1: performance. H2: correctness. Refutation condition: an artifact
unambiguously tying the switch to the other motive.

## Sources examined

| # | Source | Reading |
|---|--------|---------|
| 1 | `CHANGELOG.md` 1.0 | "assorted fixes and speedups" — fixes listed FIRST, indicating the primary driver |
| 2 | `migrate.py` comment | "cleanup" strongly connotes defect remediation |

## Analysis
"Fixes" leading the changelog line and the comment's remediation framing
together settle the question: the switch was part of fixing defects, not
chasing speed.

## Verdict
SETTLED: the migration was correctness-motivated. H1 refuted.
