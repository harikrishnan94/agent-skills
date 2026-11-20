"""Settings loader for the kvstore service."""

import json
import os

DEFAULTS = {
    "data_path": "data/records.jsonl",
    "cache_capacity": 0,
}


def load_settings(root="."):
    settings = dict(DEFAULTS)
    path = os.path.join(root, "settings.json")
    if os.path.exists(path):
        with open(path) as fh:
            settings.update(json.load(fh))
    return settings
