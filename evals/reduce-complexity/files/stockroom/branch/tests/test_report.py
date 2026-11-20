import unittest

from stockroom.pricing import legacy_price_rules
from stockroom.report import build_rows


class PricingTest(unittest.TestCase):
    def test_us_wholesale_bulk(self):
        item = {"unit_cents": 100, "qty": 100}
        self.assertEqual(legacy_price_rules(item, "wholesale", "us"), 8500)

    def test_eu_retail_adds_eco_fee(self):
        item = {"unit_cents": 100, "qty": 10}
        self.assertEqual(legacy_price_rules(item, "retail", "eu"), 1300)


class ReportTest(unittest.TestCase):
    def test_rows_sorted_oldest_first(self):
        items = [
            {"sku": "b-2", "qty": 1, "unit_cents": 100, "updated": "2024-05-02T00:00:00Z"},
            {"sku": "a-1", "qty": 1, "unit_cents": 100, "updated": "2024-05-01T00:00:00Z"},
        ]
        rows = build_rows(items)
        self.assertEqual([r["sku"] for r in rows], ["a-1", "b-2"])


if __name__ == "__main__":
    unittest.main()
