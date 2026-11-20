import json
import os
import tempfile
import unittest

from store import Store
from store import v2


class StoreRoundTrip(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "test.store")

    def test_put_then_get(self):
        s = Store(self.path)
        s.put("alpha", "one")
        s.put("beta", "two")
        self.assertEqual(s.get("alpha"), "one")
        self.assertEqual(s.get("beta"), "two")

    def test_overwrite(self):
        s = Store(self.path)
        s.put("alpha", "one")
        s.put("alpha", "uno")
        self.assertEqual(s.get("alpha"), "uno")

    def test_missing_key(self):
        s = Store(self.path)
        s.put("alpha", "one")
        with self.assertRaises(KeyError):
            s.get("nope")

    def test_keys_sorted(self):
        s = Store(self.path)
        s.put("b", "2")
        s.put("a", "1")
        self.assertEqual(s.keys(), ["a", "b"])

    def test_header_written(self):
        s = Store(self.path)
        s.put("alpha", "one")
        with open(self.path) as fh:
            header = json.loads(fh.readline())
        self.assertEqual(header, {"format": "docstore", "version": 2})

    def test_rejects_headerless_file(self):
        with open(self.path, "w") as fh:
            fh.write('{"key": "a", "value": "1"}\n')
        with self.assertRaises(ValueError):
            v2.read_records(self.path)


if __name__ == "__main__":
    unittest.main()
