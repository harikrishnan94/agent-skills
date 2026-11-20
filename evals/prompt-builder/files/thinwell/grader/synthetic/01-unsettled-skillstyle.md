# Migration rationale investigation — result: NO-RESULT

## Question
Was the v1→v2 storage migration motivated by performance or by correctness?

## Evidence matrix

| # | Source | Supports performance? | Supports correctness? | Independent? |
|---|--------|----------------------|----------------------|--------------|
| 1 | `migrate.py` comment ("v2 format introduced during the 1.x cleanup") | neutral | neutral | — |
| 2 | `CHANGELOG.md` 1.0 ("switched storage to the v2 format; assorted fixes and speedups") | weakly | weakly | correlated with #1 (same release) |

## Convergence assessment
Two sources, mutually correlated (both artifacts of the same 1.0 release
housekeeping), each compatible with both hypotheses. Convergence criterion
not met. Git history is a single squashed import commit; no pre-migration
code, benchmarks, bug reports, or design notes survive in the repo.

## Verdict
UNSETTLED. The available material does not determine the motive. Recording a
NO-RESULT rather than forcing a conclusion.

## What would settle it
- The pre-squash commit history from the internal repo
- The original v1 implementation (to test for defects or benchmark)
- An issue tracker or design doc from the departed team
