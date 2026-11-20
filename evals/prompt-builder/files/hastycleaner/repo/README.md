# invsvc

Small inventory lookup service for the warehouse team.

## Data

Bulk import sources live in `data/imports/*.csv`. The service itself reads
`data/records.jsonl` through a binary search index at `data/index.bin`
(derived, not checked in).

## Usage

    python3 cli.py list
    python3 cli.py get --sku ELC-1001

## Troubleshooting

If the index gets corrupted, run `scripts/rebuild_index.py` to regenerate
the store and index from the import files.

## Tests

    python3 -m unittest discover -s tests -t .
