# feedproc

Small tool for working with vendor feed files (CSV).

Usage:

    python3 cli.py summary data/sample.csv
    python3 cli.py export data/sample.csv out.csv

`summary` prints row/unit/value totals and per-vendor counts. `export` writes
the feed back out as normalized CSV for downstream jobs.

Tests:

    python3 -m unittest discover -s tests -t .
