import os
import tempfile
import unittest

from feedproc.export import export_csv

HEADER = ["sku", "title", "vendor", "location", "price", "qty"]
ROWS = [
    ["AB-1", "Cable Tray", "Denbury", "Austin TX", "19.99", "42"],
    ["AB-2", "Felt Desk Pad", "Grainhouse", "Portland OR", "24.00", "30"],
]


class ExportTests(unittest.TestCase):
    def test_writes_header_and_rows(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            export_csv(HEADER, ROWS, path)
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        finally:
            os.unlink(path)
        self.assertEqual(lines[0], "sku,title,vendor,location,price,qty")
        self.assertEqual(lines[1], "AB-1,Cable Tray,Denbury,Austin TX,19.99,42")
        self.assertEqual(len(lines), 3)

    def test_returns_row_count(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            self.assertEqual(export_csv(HEADER, ROWS, path), 2)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
