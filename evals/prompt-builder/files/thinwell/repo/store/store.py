import os

from . import v2


class Store:
    """A small key/value document store backed by a single v2 file."""

    def __init__(self, path):
        self.path = path

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        return v2.read_records(self.path)

    def put(self, key, value):
        records = self._load()
        records[key] = value
        v2.write_records(self.path, records)

    def get(self, key):
        records = self._load()
        if key not in records:
            raise KeyError(key)
        return records[key]

    def keys(self):
        return sorted(self._load())
