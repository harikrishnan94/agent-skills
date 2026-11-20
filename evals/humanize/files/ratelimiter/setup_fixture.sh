#!/bin/bash
# Build the ratelimiter fixture repo at $1: base history on main, then the
# AI-telly burst-limits change committed on feature/add-burst-limits.
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
git add .gitignore ratelimit/__init__.py ratelimit/bucket.py
git commit -qm "add token bucket"
git add ratelimit/middleware.py
git commit -qm "add request middleware"
git add ratelimit/config.py tests
git commit -qm "add config loader"
git tag fixture-base

git checkout -qb feature/add-burst-limits
cp -R "$SRC/telly/." .
git add -A
git commit -qm "feat: Added Burst Limits Functionality 🚀

- Added BurstLimitManager class for managing burst limits
- Updated config with new burst option
- Added comprehensive tests
- Improved code formatting in bucket.py

🤖 Generated with AI"
