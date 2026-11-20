import io
import json
import unittest

from logship.batch import Batch, batch_to_rows
from logship.exporter import export_batches, export_lines
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

    def test_format_entry_json(self):
        entry = {"ts": "2024-05-01T12:00:00", "level": "WARN", "message": "disk low"}
        self.assertEqual(
            json.loads(format_entry(entry, legacy=False)),
            {"ts": "2024-05-01T12:00:00", "level": "WARN", "msg": "disk low"},
        )


class TestExport(unittest.TestCase):
    def test_export_lines(self):
        src = ["2024-05-01T12:00:00 INFO a\n", "\n", "2024-05-01T12:00:01 WARN b\n"]
        out = io.StringIO()
        self.assertEqual(export_lines(src, out), 2)
        rows = [json.loads(r) for r in out.getvalue().splitlines()]
        self.assertEqual([r["msg"] for r in rows], ["a", "b"])

    def test_export_batches(self):
        src = ["2024-05-01T12:00:0%d INFO m%d\n" % (i, i) for i in range(5)]
        out = io.StringIO()
        self.assertEqual(export_batches(src, out, size=2), 5)
        rows = [json.loads(r) for r in out.getvalue().splitlines()]
        self.assertEqual([r["msg"] for r in rows], ["m0", "m1", "m2", "m3", "m4"])

    def test_batch_to_rows(self):
        batch = Batch()
        batch.add({"ts": "2024-05-01T12:00:00", "level": "INFO", "message": "x"})
        rows = batch_to_rows(batch)
        self.assertEqual(json.loads(rows[0])["msg"], "x")
