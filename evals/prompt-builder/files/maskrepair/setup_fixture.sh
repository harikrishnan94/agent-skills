#!/bin/bash
# Build the feedproc fixture repo at $1.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$1"

mkdir -p "$DEST"
cd "$DEST"
git init -q -b main
git config user.name "Ana Ferreira"
git config user.email "ana@example.com"
git config commit.gpgsign false  # a signing setup on the host must not leak into the fixture
git config tag.gpgsign false

cp -R "$SRC/repo/." .
find . -name __pycache__ -type d -prune -exec rm -rf {} +

git add README.md feedproc/__init__.py feedproc/parser.py feedproc/summary.py
git commit -qm "add feed parsing and summary rendering"

git add cli.py feedproc/export.py
git commit -qm "add cli with summary and export subcommands"

git add tests data/sample.csv
git commit -qm "add tests and vendor sample feed"

git add ISSUE.md
git commit -qm "note summary crash on the vendor sample feed"
