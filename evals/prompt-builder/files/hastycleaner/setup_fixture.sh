#!/bin/bash
# Build the hastycleaner fixture repo at $1: bulk-import era first, then the
# manual-add feature and the hand-entered records, then the startup-failure
# note. data/index.bin (untracked, derived) is left truncated in the working
# tree. Commit dates are pinned so repeated builds produce identical trees.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$1"

mkdir -p "$DEST"
cd "$DEST"
git init -q -b main
git config user.name "Priya Nair"
git config user.email "priya@example.com"
git config commit.gpgsign false  # a signing setup on the host must not leak into the fixture
git config tag.gpgsign false

commit() { # commit <iso-date> <message>
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git commit -qm "$2"
}

# --- bulk-import era ---------------------------------------------------
mkdir -p invsvc scripts data/imports tests
cp "$SRC/repo/.gitignore" .gitignore
cp "$SRC/repo/invsvc/__init__.py" "$SRC/repo/invsvc/store.py" "$SRC/repo/invsvc/index.py" invsvc/
cp "$SRC/repo/tests/__init__.py" "$SRC/repo/tests/test_store.py" "$SRC/repo/tests/test_index.py" tests/
git add .gitignore invsvc tests
commit "2026-02-10T09:14:00 +0000" "add record store and binary search index"

cp "$SRC/stages/cli_v1.py" cli.py
cp "$SRC/repo/README.md" README.md
cp "$SRC/repo/data/imports/electronics.csv" "$SRC/repo/data/imports/warehouse.csv" data/imports/
cp "$SRC/stages/records_bulk.jsonl" data/records.jsonl
git add cli.py README.md data
commit "2026-02-11T15:40:00 +0000" "add cli and initial warehouse import"

cp "$SRC/repo/scripts/rebuild_index.py" scripts/rebuild_index.py
git add scripts
commit "2026-02-12T10:05:00 +0000" "add recovery script: regenerate store and index from imports"

# --- manual-entry era ---------------------------------------------------
cp "$SRC/repo/cli.py" cli.py
git add cli.py
commit "2026-05-04T11:22:00 +0000" "cli: add 'add' and 'reindex' commands for hand-entered stock"

cat "$SRC/stages/records_manual1.jsonl" >> data/records.jsonl
git add data/records.jsonl
commit "2026-05-06T16:03:00 +0000" "record refurb and demo stock taken in at the counter"

cat "$SRC/stages/records_manual2.jsonl" >> data/records.jsonl
git add data/records.jsonl
commit "2026-06-17T09:47:00 +0000" "add front-desk spares and trade-in batch"

cp "$SRC/repo/ISSUE.md" ISSUE.md
git add ISSUE.md
commit "2026-07-12T08:31:00 +0000" "capture startup traceback"

# --- working-tree state: derived index present but truncated -------------
python3 - "$DEST" <<'EOF'
import os
import sys
dest = sys.argv[1]
sys.path.insert(0, dest)
from invsvc.index import build_from_store
build_from_store(os.path.join(dest, "data", "records.jsonl"),
                 os.path.join(dest, "data", "index.bin"))
EOF
head -c 173 data/index.bin > data/index.bin.part
mv data/index.bin.part data/index.bin
