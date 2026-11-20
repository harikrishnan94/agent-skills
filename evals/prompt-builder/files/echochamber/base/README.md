# kvstore

Small key-value lookup service used by the data tooling team. Records live in
a JSONL file; lookups go through an in-process read-through cache backed by a
line-scan of the records file.

## Usage

    python3 cli.py load data/records.jsonl
    python3 cli.py lookup --key user-000123
    python3 cli.py lookup --key user-000123 --repeat 100

## Tests

    python3 -m unittest discover -s tests -t .
