#!/bin/bash
# Build the logship fixture repo at $1: base history on main, then the batch
# export work built up in five commits on feature/batch-export (left checked
# out). The branch plants three structural accretions for reduce-complexity
# to find: a constant-threaded legacy flag, an orphaned _chunk helper, and a
# batch_to_rows adapter between two shapes both introduced on the branch.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$1"

mkdir -p "$DEST"
cd "$DEST"
git init -q -b main
git config user.name "Dev"
git config user.email "dev@example.com"
git config commit.gpgsign false  # a signing setup on the host must not leak into the fixture
git config tag.gpgsign false

cp -R "$SRC/base/." .
git add .gitignore logship/__init__.py logship/records.py
git commit -qm "add log record parsing"
git add logship/exporter.py logship/cli.py
git commit -qm "add line exporter and cli"
git add tests
git commit -qm "add export tests"
git tag fixture-base

git checkout -qb feature/batch-export

# branch commit 1: BatchWriter lands first (final form from day one)
cp "$SRC/branch/logship/writer.py" logship/writer.py
git add -A
git commit -qm "add batch writer"

# branch commit 2: JSON format arrives behind a legacy flag; every caller
# passes legacy=True so behavior is preserved while the format stabilizes
cp "$SRC/branch/logship/records.py" logship/records.py
cat > logship/exporter.py <<'EOF'
from logship.records import format_entry, parse_line


def export_lines(lines, out):
    n = 0
    for line in lines:
        if not line.strip():
            continue
        out.write(format_entry(parse_line(line), legacy=True) + "\n")
        n += 1
    return n
EOF
cat > tests/test_export.py <<'EOF'
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

    def test_format_entry_legacy(self):
        entry = {"ts": "2024-05-01T12:00:00", "level": "WARN", "message": "disk low"}
        self.assertEqual(
            format_entry(entry, legacy=True), "2024-05-01T12:00:00 [WARN] disk low"
        )


class TestExport(unittest.TestCase):
    def test_export_lines(self):
        src = ["2024-05-01T12:00:00 INFO a\n", "\n", "2024-05-01T12:00:01 WARN b\n"]
        out = io.StringIO()
        self.assertEqual(export_lines(src, out), 2)
        self.assertEqual(
            out.getvalue().splitlines(),
            ["2024-05-01T12:00:00 [INFO] a", "2024-05-01T12:00:01 [WARN] b"],
        )
EOF
git add -A
git commit -qm "add json format behind legacy flag"

# branch commit 3: batched export built on a _chunk generator
cat > logship/exporter.py <<'EOF'
from logship.records import format_entry, parse_line
from logship.writer import BatchWriter


def _chunk(records, size):
    batch = []
    for rec in records:
        batch.append(rec)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def export_lines(lines, out):
    n = 0
    for line in lines:
        if not line.strip():
            continue
        out.write(format_entry(parse_line(line), legacy=True) + "\n")
        n += 1
    return n


def export_batches(lines, out, size=100):
    writer = BatchWriter(out)
    entries = (parse_line(line) for line in lines if line.strip())
    for group in _chunk(entries, size):
        writer.write([format_entry(e, legacy=True) for e in group])
    return writer.count
EOF
cp "$SRC/branch/logship/cli.py" logship/cli.py
cat > tests/test_export.py <<'EOF'
import io
import unittest

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

    def test_format_entry_legacy(self):
        entry = {"ts": "2024-05-01T12:00:00", "level": "WARN", "message": "disk low"}
        self.assertEqual(
            format_entry(entry, legacy=True), "2024-05-01T12:00:00 [WARN] disk low"
        )


class TestExport(unittest.TestCase):
    def test_export_lines(self):
        src = ["2024-05-01T12:00:00 INFO a\n", "\n", "2024-05-01T12:00:01 WARN b\n"]
        out = io.StringIO()
        self.assertEqual(export_lines(src, out), 2)
        self.assertEqual(
            out.getvalue().splitlines(),
            ["2024-05-01T12:00:00 [INFO] a", "2024-05-01T12:00:01 [WARN] b"],
        )

    def test_export_batches(self):
        src = ["2024-05-01T12:00:0%d INFO m%d\n" % (i, i) for i in range(5)]
        out = io.StringIO()
        self.assertEqual(export_batches(src, out, size=2), 5)
        self.assertEqual(len(out.getvalue().splitlines()), 5)
EOF
git add -A
git commit -qm "add chunked batch export"

# branch commit 4: Batch model lands, JSON becomes the output format, and
# every caller flips from legacy=True to legacy=False
cp "$SRC/branch/logship/batch.py" logship/batch.py
cp "$SRC/branch/tests/test_export.py" tests/test_export.py
cat > logship/exporter.py <<'EOF'
from logship.batch import Batch, batch_to_rows
from logship.records import format_entry, parse_line
from logship.writer import BatchWriter


def _chunk(records, size):
    batch = []
    for rec in records:
        batch.append(rec)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def export_lines(lines, out):
    n = 0
    for line in lines:
        if not line.strip():
            continue
        out.write(format_entry(parse_line(line), legacy=False) + "\n")
        n += 1
    return n


def export_batches(lines, out, size=100):
    writer = BatchWriter(out)
    entries = (parse_line(line) for line in lines if line.strip())
    for group in _chunk(entries, size):
        batch = Batch()
        for entry in group:
            batch.add(entry)
        writer.write(batch_to_rows(batch))
    return writer.count
EOF
git add -A
git commit -qm "add batch model and default to json"

# branch commit 5: export_batches accumulates and flushes directly, which
# orphans _chunk; final tree is exactly the branch/ overlay
cp -R "$SRC/branch/." .
git add -A
git commit -qm "flush batches inline in exporter"
git tag fixture-head
