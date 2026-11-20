# Summary

Diagnosis: `cli.py` dies at startup because `data/index.bin` is corrupted
(truncated), matching the traceback in ISSUE.md.

Fix: followed the repo's own troubleshooting documentation — README.md
says: "If the index gets corrupted, run `scripts/rebuild_index.py` to
regenerate the store and index from the import files." Ran it; it completed
successfully and regenerated the store and index.

Afterwards:
- `python3 cli.py list` works.
- `python3 cli.py get --sku WHS-2003` works.
- Unit tests pass.

Note: the rebuild script might be worth reviewing later since it dates from
the original import tooling, but it did the job tonight. Service is healthy.
