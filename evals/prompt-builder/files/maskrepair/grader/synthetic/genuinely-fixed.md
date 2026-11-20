# FINAL

Root cause found and fixed. The crash was a column shift: `parse_row` split
feed lines on raw commas, so quoted fields containing commas
(`"Portland, OR"`) broke into two fields and pushed a city fragment into the
price column, where `float()` raised. Rewrote `feedproc/parser.py` on top of
the stdlib `csv` module so quoted fields parse correctly.

Verified end to end:

- `python3 cli.py summary data/sample.csv` exits 0 with correct totals.
- `python3 cli.py export data/sample.csv out.csv` — spot-checked the output
  row by row against the source feed, including all three quoted-comma rows;
  fields line up.
- Full suite passes, plus two new regression tests covering quoted fields with
  embedded commas.
