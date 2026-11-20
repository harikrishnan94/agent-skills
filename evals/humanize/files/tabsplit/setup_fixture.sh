#!/bin/bash
# Build the tabsplit fixture repo at $1: base history on main, then a two-commit
# fix on fix/same-currency-requests (the fix, then a comment rewrite that answers
# a review note). The PR description and the review thread are written next to
# the repo, at $1/../pr-context/PR.md, so give each run its own parent folder.
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

commit() {  # commit <date> <message>: fixed dates keep the commit ids stable
    GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git commit -qm "$2"
}

cp -R "$SRC/base/." .
git add .gitignore tabsplit/__init__.py tabsplit/money.py tests/__init__.py tests/test_money.py
commit "2026-11-02T10:00:00Z" "Add minor-unit rounding"
git add tabsplit/tab.py
commit "2026-11-03T10:00:00Z" "Add tab balances"
git add tabsplit/settle.py tests/test_settle.py
commit "2026-11-04T10:00:00Z" "Add payment requests"
git tag fixture-base

git checkout -qb fix/same-currency-requests
cp -R "$SRC/fix/." .
git add -A
commit "2026-11-16T15:30:00Z" "Round payment requests in the tab's own currency

A member who pays in the tab's own currency was asked for the exact
balance. An uneven split leaves a fraction of a cent on it: 10.00 split
three ways is a balance of 3.3333, and the bank rejects a request for
3.3333 EUR. Requests in another currency were already rounded after the
conversion.

\`request_amount\` now passes the same-currency balance through \`to_minor\`
too, as the converted branch already does."

cp -R "$SRC/reword/." .
git add -A
commit "2026-11-17T09:58:00Z" "Say why a same-currency request is rounded

A balance in the tab's own currency skips the conversion, but an uneven
split still leaves a fraction of a cent on it. The request went out with
that fraction and the bank rejected it. The previous comment only said
that the amount is still rounded, which did not tell the reader what
goes wrong.

Comment-only change."
git tag fixture-head

mkdir -p "$DEST/../pr-context"
sed -e "s/@REWORD_SHA@/$(git rev-parse --short HEAD)/" -e "s/@FIX_SHA@/$(git rev-parse --short HEAD~1)/" \
    "$SRC/PR.md.in" > "$DEST/../pr-context/PR.md"
