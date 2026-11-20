import json
import os
import tempfile
import unittest

from ledger import store


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "ledger.json")

    def test_load_missing_file_returns_empty_ledger(self):
        self.assertEqual(store.load(self.path), {"accounts": {}})

    def test_round_trip(self):
        data = {"accounts": {"acme": {"transactions": []}}}
        store.save(self.path, data)
        self.assertEqual(store.load(self.path), data)

    def test_save_replaces_previous_contents(self):
        store.save(self.path, {"accounts": {"old": {"transactions": []}}})
        store.save(self.path, {"accounts": {}})
        self.assertEqual(store.load(self.path), {"accounts": {}})

    def test_save_writes_valid_json(self):
        store.save(self.path, {"accounts": {}})
        with open(self.path) as fh:
            self.assertEqual(json.load(fh), {"accounts": {}})
