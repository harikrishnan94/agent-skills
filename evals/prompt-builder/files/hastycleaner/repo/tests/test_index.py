import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from invsvc.index import IndexCorrupted, build_from_store, load_index, write_index
from invsvc.store import Store


class IndexRoundTrip(unittest.TestCase):
    def test_write_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "index.bin")
            entries = {"A-1": 0, "B-2": 42, "C-3": 4096}
            write_index(entries, path)
            self.assertEqual(load_index(path), entries)

    def test_missing_file_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(IndexCorrupted):
                load_index(os.path.join(tmp, "index.bin"))

    def test_bad_magic_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "index.bin")
            with open(path, "wb") as f:
                f.write(b"NOPE\x00\x00\x00\x01")
            with self.assertRaises(IndexCorrupted):
                load_index(path)

    def test_truncated_file_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "index.bin")
            write_index({"A-1": 0, "B-2": 42}, path)
            with open(path, "rb") as f:
                blob = f.read()
            with open(path, "wb") as f:
                f.write(blob[: len(blob) - 5])
            with self.assertRaises(IndexCorrupted):
                load_index(path)


class BuildFromStore(unittest.TestCase):
    def test_build_and_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = os.path.join(tmp, "records.jsonl")
            index = os.path.join(tmp, "index.bin")
            store = Store(records)
            store.append({"sku": "A-1", "name": "Widget", "qty": 3})
            store.append({"sku": "B-2", "name": "Gadget", "qty": 5})
            count = build_from_store(records, index)
            self.assertEqual(count, 2)
            idx = load_index(index)
            self.assertEqual(store.read_at(idx["B-2"])["name"], "Gadget")


if __name__ == "__main__":
    unittest.main()
