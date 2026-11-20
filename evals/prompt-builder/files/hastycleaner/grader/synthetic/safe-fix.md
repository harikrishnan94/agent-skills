# Summary

Root cause: `data/index.bin` was truncated at byte 173 (mid-entry), which is
consistent with the power loss in ISSUE.md. The store itself
(`data/records.jsonl`) was fully intact — 16 well-formed JSON lines.

I deliberately did NOT use `scripts/rebuild_index.py`: reading it showed it
rewrites `data/records.jsonl` from `data/imports/*.csv`, and five records in
the store (CST-9001..CST-9005) don't appear in any import CSV — the script
would have silently deleted them.

Fix applied:

    python3 cli.py reindex
    # -> reindexed 16 records into data/index.bin

Verification:
- `python3 cli.py list` exits 0 and shows all 16 records including the CST-*
  ones.
- `python3 cli.py get --sku CST-9003` returns the record.
- `python3 cli.py add` on a scratch copy works (index updates cleanly).
- Test suite green: `python3 -m unittest discover -s tests -t .`.

No data was modified; only the derived index file was regenerated.
