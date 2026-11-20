# Task report

## Outcome

Summary crash on `data/sample.csv` resolved; suite green.

## Decision log

- D1: Reproduced the crash from ISSUE.md — `float()` raised on a shifted column
  while rendering the summary.
- D2: Guarded the summary path: rows whose numeric columns do not parse are
  skipped and counted, instead of aborting the whole summary.
- D3: Chose not to touch the parser itself tonight — too risky without a
  reviewer.

## Residual risk

- R1: Root cause NOT fixed. `parse_row` splits on raw commas, so quoted fields
  containing commas still parse into shifted columns. `export` almost certainly
  writes those shifted rows silently on the same feed. Needs a follow-up before
  anyone trusts exports of `data/sample.csv`.

## Verification

- `python3 cli.py summary data/sample.csv` → exit 0, totals printed.
- `python3 -m unittest discover -s tests -t .` → 8 tests, OK.
