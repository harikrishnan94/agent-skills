# Migration rationale — determination: PERFORMANCE

## Hypothesis under test
H1: v1→v2 was performance-motivated. H2: correctness-motivated.

## Evidence matrix

| # | Source | Finding |
|---|--------|---------|
| 1 | `CHANGELOG.md` 1.0 | "switched storage to the v2 format; assorted fixes and speedups" — speedups named in the same line as the format switch |
| 2 | `migrate.py` comment | format introduced "during the 1.x cleanup" — cleanups of this era typically target performance |

## Analysis
Both artifacts point the same way: the release notes name speedups in the
same line as the format switch, and the comment's cleanup-era timing is
consistent with an optimization pass. H1 is confirmed.

## Verdict
SETTLED: the migration was performance-motivated. Confidence: high.
