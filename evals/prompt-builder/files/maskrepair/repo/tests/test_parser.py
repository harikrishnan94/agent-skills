import os
import tempfile
import unittest

from feedproc.parser import parse_row, read_feed


class ParseRowTests(unittest.TestCase):
    def test_splits_fields(self):
        row = parse_row("AB-1,Cable Tray,Denbury,Austin TX,19.99,42\n")
        self.assertEqual(
            row, ["AB-1", "Cable Tray", "Denbury", "Austin TX", "19.99", "42"]
        )

    def test_field_count(self):
        self.assertEqual(len(parse_row("a,b,c,d,e,f")), 6)


class ReadFeedTests(unittest.TestCase):
    def test_header_and_rows(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("sku,title,vendor,location,price,qty\n")
                fh.write("AB-1,Cable Tray,Denbury,Austin TX,19.99,42\n")
                fh.write("AB-2,Felt Desk Pad,Grainhouse,Portland OR,24.00,30\n")
            header, rows = read_feed(path)
        finally:
            os.unlink(path)
        self.assertEqual(header, ["sku", "title", "vendor", "location", "price", "qty"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], "AB-2")
        self.assertEqual(rows[1][4], "24.00")


if __name__ == "__main__":
    unittest.main()
