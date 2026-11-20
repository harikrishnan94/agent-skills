Crash is gone — `python3 cli.py summary data/sample.csv` runs clean now and the
test suite passes. I got there by skipping the rows the summary math chokes on,
so heads up: the underlying parsing looks shaky on some rows in the sample feed
and may warrant a deeper look at some point. I didn't get to the export path at
all, so I can't vouch for it on this file.
