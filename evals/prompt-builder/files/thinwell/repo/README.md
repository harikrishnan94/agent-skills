# docstore

A small document store with a line-oriented on-disk format (v2).

## Usage

    python3 cli.py put notes.store greeting "hello"
    python3 cli.py get notes.store greeting
    python3 cli.py list notes.store

Legacy v1 files can be converted with:

    python3 migrate.py data/legacy_2019.v1 converted.store

## Tests

    python3 -m unittest discover -s tests -t .
