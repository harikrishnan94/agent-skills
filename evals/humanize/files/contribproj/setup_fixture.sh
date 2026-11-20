#!/bin/bash
# Build the contribproj fixture repo at $1: base history, then the parser fix
# left UNCOMMITTED in the working tree. The eval task is collateral only.
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

cp "$SRC/CONTRIBUTING.md" .
cp -R "$SRC/base/." .
# first commit predates key/value whitespace stripping
perl -pi -e 's/\Qpairs[key.strip()] = val.strip()\E/pairs[key] = val/' src/parser.py
git add .gitignore CONTRIBUTING.md src/__init__.py src/parser.py tests
git commit -qm "add key=value parser"
git add src/main.py
git commit -qm "add cli entry point"
cp "$SRC/base/src/parser.py" src/parser.py
git add src/parser.py
git commit -qm "strip whitespace around keys and values"
git tag fixture-base

# the AI-written fix, staged in the working tree only
cp "$SRC/fixed/src/parser.py" src/parser.py
cp "$SRC/fixed/tests/test_parser.py" tests/test_parser.py
