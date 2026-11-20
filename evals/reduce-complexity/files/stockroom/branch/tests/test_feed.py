import json
import os
import tempfile
import unittest

from stockroom.feed import load_feed


class FeedTest(unittest.TestCase):
    def _write(self, records):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(records, f)
        self.addCleanup(os.unlink, path)
        return path

    def test_skips_malformed_records(self):
        path = self._write([
            {"sku": "a-1", "qty": 4},
            {"qty": 2},
            None,
            {"sku": "b-2"},
        ])
        items = load_feed(path)
        self.assertEqual(
            [(i["sku"], i["qty"]) for i in items],
            [("a-1", 4), ("b-2", 0)],
        )


if __name__ == "__main__":
    unittest.main()
