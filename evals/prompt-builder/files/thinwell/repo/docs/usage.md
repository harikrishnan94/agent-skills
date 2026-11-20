# Using docstore

The store is a single file; every command takes the file path first.

## Commands

Store a value:

    python3 cli.py put team.store owner "platform team"

Read it back:

    python3 cli.py get team.store owner

List all keys:

    python3 cli.py list team.store

`get` exits nonzero and prints to stderr when the key is missing.

## Converting old files

Files written by pre-1.0 versions use the v1 layout and are not readable by
the current tool. Convert them once with:

    python3 migrate.py old-file.v1 new-file.store
