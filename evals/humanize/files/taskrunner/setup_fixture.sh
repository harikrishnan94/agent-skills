#!/bin/bash
# Build the taskrunner fixture repo at $1 with its 3-commit base history.
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
# first commit predates the missing-ts fix
perl -pi -e 's/\Qr.get("ts", 0)\E/r["ts"]/' taskq/store.py
git add .gitignore taskq/__init__.py taskq/store.py tests
git commit -qm "add task store with atomic write"

git add taskq/cli.py taskq/fmt.py
git commit -qm "add cli with add/ls/done"

cp "$SRC/base/taskq/store.py" taskq/store.py
git add taskq/store.py
git commit -qm "fix ls ordering on missing ts"

git tag fixture-base
