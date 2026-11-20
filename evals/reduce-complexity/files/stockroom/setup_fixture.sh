#!/bin/bash
# Build the stockroom fixture repo at $1: base history on main, then the
# export work spread across five commits on feature/export-formats.
# Intermediate states live in heredocs below; files whose commit state is
# already final are taken straight from branch/ so the tip tree exactly
# equals the branch/ overlay.
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
git add .gitignore stockroom/__init__.py stockroom/util.py
git commit -qm "add package skeleton and timestamp util"
git add stockroom/pricing.py
git commit -qm "add legacy price rules"
git add stockroom/report.py tests
git commit -qm "add report rows and tests"
git tag fixture-base

git checkout -qb feature/export-formats

# commit 1: csv export; timestamps pass through raw
cat > stockroom/export.py <<'EOF'
import csv
import io

FIELDS = ["sku", "qty", "total_cents", "updated"]


def export_csv(rows):
    cleaned = []
    for row in rows:
        if not row.get("sku"):
            continue
        qty = row.get("qty", 0)
        if qty < 0:
            qty = 0
        cleaned.append({**row, "qty": qty})
    cleaned.sort(key=lambda r: r["sku"])
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    for row in cleaned:
        writer.writerow({
            "sku": row["sku"],
            "qty": row["qty"],
            "total_cents": row.get("total_cents", 0),
            "updated": row.get("updated") or "",
        })
    return buf.getvalue()
EOF
git add stockroom/export.py
git commit -qm "add csv export"

# commit 2: json export grows its own copy of the row normalization
cat > stockroom/export.py <<'EOF'
import csv
import io
import json

FIELDS = ["sku", "qty", "total_cents", "updated"]


def export_csv(rows):
    cleaned = []
    for row in rows:
        if not row.get("sku"):
            continue
        qty = row.get("qty", 0)
        if qty < 0:
            qty = 0
        cleaned.append({**row, "qty": qty})
    cleaned.sort(key=lambda r: r["sku"])
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    for row in cleaned:
        writer.writerow({
            "sku": row["sku"],
            "qty": row["qty"],
            "total_cents": row.get("total_cents", 0),
            "updated": row.get("updated") or "",
        })
    return buf.getvalue()


def export_json(rows):
    keep = []
    for entry in rows:
        if not entry.get("sku"):
            continue
        count = entry.get("qty", 0)
        if count < 0:
            count = 0
        keep.append({**entry, "qty": count})
    keep.sort(key=lambda e: e["sku"])
    out = []
    for entry in keep:
        out.append({
            "sku": entry["sku"],
            "qty": entry["qty"],
            "total_cents": entry.get("total_cents", 0),
            "updated": entry.get("updated"),
        })
    return json.dumps(out, indent=2)
EOF
git add stockroom/export.py
git commit -qm "add json export"

# commit 3: local iso8601 parser to render timestamps as epoch
cp "$SRC/branch/stockroom/export.py" stockroom/export.py
git add stockroom/export.py
git commit -qm "render export timestamps as epoch"

# commit 4: one-line region tweak inside the old pricing rules
cp "$SRC/branch/stockroom/pricing.py" stockroom/pricing.py
git add stockroom/pricing.py
git commit -qm "handle eu-north region in price rules"

# commit 5: feed loader plus tests; tip tree now equals branch/
cp -R "$SRC/branch/." .
git add -A
git commit -qm "add feed loader and export tests"
git tag fixture-head
