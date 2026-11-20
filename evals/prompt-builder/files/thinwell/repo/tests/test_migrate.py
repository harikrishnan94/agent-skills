import os
import tempfile
import unittest

import migrate
from store import v2

SAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "legacy_2019.v1",
)


class MigrateV1(unittest.TestCase):
    def test_sample_parses(self):
        records = migrate.read_v1(SAMPLE)
        self.assertEqual(len(records), 6)
        self.assertIn("invoice-1001", records)

    def test_migrated_file_readable(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.store")
            records = migrate.read_v1(SAMPLE)
            v2.write_records(out, records)
            self.assertEqual(v2.read_records(out), records)

    def test_rejects_non_v1_input(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.store")
            v2.write_records(out, {"a": "1"})
            with self.assertRaises(ValueError):
                migrate.read_v1(out)


if __name__ == "__main__":
    unittest.main()
