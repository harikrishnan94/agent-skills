import json
import unittest

from stockroom.export import export_csv, export_json

ROWS = [
    {"sku": "b-2", "qty": 3, "total_cents": 300, "updated": "2024-05-01T12:00:00Z"},
    {"sku": "a-1", "qty": -1, "total_cents": 0, "updated": None},
    {"sku": None, "qty": 5, "total_cents": 500, "updated": None},
]


class ExportCsvTest(unittest.TestCase):
    def test_skips_missing_sku_and_clamps_qty(self):
        lines = export_csv(ROWS).strip().splitlines()
        self.assertEqual(lines[0], "sku,qty,total_cents,updated")
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[1].startswith("a-1,0,"))

    def test_renders_epoch(self):
        out = export_csv([ROWS[0]])
        self.assertIn("1714564800", out)


class ExportJsonTest(unittest.TestCase):
    def test_matches_csv_normalization(self):
        data = json.loads(export_json(ROWS))
        self.assertEqual([r["sku"] for r in data], ["a-1", "b-2"])
        self.assertEqual(data[0]["qty"], 0)
        self.assertEqual(data[1]["updated"], "1714564800")


if __name__ == "__main__":
    unittest.main()
