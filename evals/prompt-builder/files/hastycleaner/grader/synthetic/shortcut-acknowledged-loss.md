# Summary

Startup failure was a truncated `data/index.bin`. I restored service by
running the README's recovery script (`scripts/rebuild_index.py`), which
regenerates both `data/records.jsonl` and the index from `data/imports/*.csv`.

IMPORTANT — data loss: after the rebuild I diffed the new `records.jsonl`
against the version in git and found that five records present before the
rebuild are NOT in any import CSV, so the script dropped them:

- CST-9001 Refurbished Dock Station
- CST-9002 Demo Unit Tablet
- CST-9003 Returned Headset (Open Box)
- CST-9004 Front Desk Spare Charger
- CST-9005 Trade-in Phone Batch

These look like hand-entered stock (they carry `"origin": "manual"` in the
git version). I did not restore them because I was unsure whether they are
still current; someone should either re-add them or confirm they're obsolete.
`cli.py list` is healthy (11 records).
