import unittest

from feedproc.summary import render_summary

HEADER = ["sku", "title", "vendor", "location", "price", "qty"]


class SummaryTests(unittest.TestCase):
    def rows(self):
        return [
            ["AB-1", "Cable Tray", "Denbury", "Austin TX", "10.00", "2"],
            ["AB-2", "Felt Desk Pad", "Grainhouse", "Portland OR", "5.50", "4"],
        ]

    def test_totals(self):
        text = render_summary(HEADER, self.rows())
        self.assertIn("rows: 2", text)
        self.assertIn("units: 6", text)
        self.assertIn("value: 42.00", text)

    def test_vendor_counts(self):
        text = render_summary(HEADER, self.rows())
        self.assertIn("Denbury: 1", text)
        self.assertIn("Grainhouse: 1", text)

    def test_empty_feed(self):
        text = render_summary(HEADER, [])
        self.assertIn("rows: 0", text)


if __name__ == "__main__":
    unittest.main()
