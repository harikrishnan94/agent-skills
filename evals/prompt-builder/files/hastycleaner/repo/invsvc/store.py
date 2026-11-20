"""Record store: one JSON object per line in data/records.jsonl."""
import json


class Store:
    def __init__(self, path):
        self.path = path

    def iter_with_offsets(self):
        """Yield (byte_offset, record) for every line in the store."""
        with open(self.path, "rb") as f:
            while True:
                offset = f.tell()
                line = f.readline()
                if not line:
                    return
                if line.strip():
                    yield offset, json.loads(line.decode("utf-8"))

    def read_at(self, offset):
        with open(self.path, "rb") as f:
            f.seek(offset)
            return json.loads(f.readline().decode("utf-8"))

    def append(self, record):
        """Append a record; returns its byte offset."""
        with open(self.path, "ab") as f:
            f.seek(0, 2)
            offset = f.tell()
            f.write((json.dumps(record) + "\n").encode("utf-8"))
        return offset
