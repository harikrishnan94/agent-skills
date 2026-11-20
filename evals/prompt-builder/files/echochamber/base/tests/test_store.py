import json
import os
import tempfile
import unittest

from kvstore.store import KVStore


class TestKVStore(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as fh:
            for i in range(10):
                fh.write(json.dumps({"key": "k%d" % i, "value": {"n": i}}) + "\n")

    def tearDown(self):
        os.unlink(self.path)

    def test_lookup_found(self):
        store = KVStore(self.path)
        self.assertEqual(store.lookup("k3"), {"n": 3})

    def test_lookup_missing(self):
        store = KVStore(self.path)
        self.assertIsNone(store.lookup("does-not-exist"))

    def test_count(self):
        self.assertEqual(KVStore(self.path).count(), 10)


if __name__ == "__main__":
    unittest.main()
