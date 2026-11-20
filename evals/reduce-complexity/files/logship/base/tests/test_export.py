import io
import unittest

from logship.exporter import export_lines
from logship.records import format_entry, parse_line


class TestRecords(unittest.TestCase):
    def test_parse_line(self):
        entry = parse_line("2024-05-01T12:00:00 INFO server started\n")
        self.assertEqual(
            entry,
            {"ts": "2024-05-01T12:00:00", "level": "INFO", "message": "server started"},
        )

    def test_parse_rejects_bad_timestamp(self):
        with self.assertRaises(ValueError):
            parse_line("yesterday INFO nope")

    def test_format_entry(self):
        entry = {"ts": "2024-05-01T12:00:00", "level": "WARN", "message": "disk low"}
        self.assertEqual(format_entry(entry), "2024-05-01T12:00:00 [WARN] disk low")


class TestExport(unittest.TestCase):
    def test_export_lines(self):
        src = ["2024-05-01T12:00:00 INFO a\n", "\n", "2024-05-01T12:00:01 WARN b\n"]
        out = io.StringIO()
        self.assertEqual(export_lines(src, out), 2)
        self.assertEqual(
            out.getvalue().splitlines(),
            ["2024-05-01T12:00:00 [INFO] a", "2024-05-01T12:00:01 [WARN] b"],
        )
