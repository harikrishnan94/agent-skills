Overnight job for the search service repo. Nobody will be awake, and no one will be available to answer questions — when something is ambiguous, make a sensible call, log the assumption in NOTES.md, and keep going.

Our search API's p95 latency got about 30% worse over the last month; we suspect the query-result cache in searchd/cache.py. Find what got slower and fix it.

Before starting any changes, write down in NOTES.md what you expect to find and roughly how much faster you expect your fix to make things — so the outcome gets compared to what you predicted instead of explained after the fact.

Measure the current speed first, on the untouched code: run make bench five times and keep all the numbers from bench/results.json. The numbers wobble as much as ten percent between runs, so compare medians of five runs and distrust any improvement smaller than the wobble.

Boundaries: the public API must not change, and leave everything outside the searchd/ directory untouched.

You are finished only when this holds in one sitting: run make bench again and the median of five runs shows p95 back near where it was a month ago, and run python -m pytest tests/ and it must pass with no failures before you say the job is done.

Nothing else may pay for the win: the rest of the service must not get slower. Check with scripts/loadtest.sh against the numbers you took at the start.

When you think you are done, start a completely separate fresh session that had no part in writing the changes and tell it to try to prove your result wrong: pick apart how you measured, look for lucky runs, read the diff for mistakes. Write what it finds into NOTES.md and deal with it.

If you cannot figure out what regressed, or the fix looks too risky to land unsupervised, say so plainly in NOTES.md — list what you checked and what is still open — instead of guessing.
