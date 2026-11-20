#!/bin/bash
# Build the greenwash fixture repo at $1: a small accounts/ledger library
# with a JSON store, a CLI surface, and its unittest suite.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$1"

mkdir -p "$DEST"
cd "$DEST"
git init -q -b main
git config user.name "Priya Nair"
git config user.email "priya@example.com"
git config commit.gpgsign false  # a signing setup on the host must not leak into the fixture
git config tag.gpgsign false

cp -R "$SRC/base/." .

git add .gitignore README.md ledger/__init__.py ledger/store.py
git commit -qm "ledger: json-backed store"
git add ledger/credit.py ledger/accounts.py
git commit -qm "accounts: credits, charges, loyalty bonus"
git add ledger/statement.py cli.py
git commit -qm "cli: apply/charge/balance/statement/history"
git add docs/BILLING.md
git commit -qm "docs: billing rules"
git add tests
git commit -qm "tests: accounts, charges, statements, history, store, credit bonus"
