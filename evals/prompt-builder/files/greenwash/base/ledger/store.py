"""JSON-backed persistence for ledger data."""

import json
import os


def load(path):
    """Load ledger data from *path*, or return an empty ledger."""
    if not os.path.exists(path):
        return {"accounts": {}}
    with open(path) as fh:
        return json.load(fh)


def save(path, data):
    """Write ledger data to *path* atomically."""
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)
