#!/bin/bash
# Build the thinwell fixture repo at $1: the docstore library, imported as a
# single squashed commit (no pre-import history survives).
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

cp -R "$SRC/repo/." .
git add -A
git commit -qm "Import from internal repo"
