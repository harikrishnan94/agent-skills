# FINAL

Fixed the crash. `python3 cli.py summary data/sample.csv` now completes and
prints the summary (12 rows). The problem was malformed rows in the sample feed
tripping the summary math; the summary path now handles them.

Verification: full test suite passes (`python3 -m unittest discover -s tests -t .`,
8 tests, OK) and the summary command exits 0. Done.
