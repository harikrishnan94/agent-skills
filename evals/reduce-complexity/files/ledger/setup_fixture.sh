#!/bin/bash
# Build the ledger fixture repo at $1: base history on main, then a three-commit
# fix for issue #42 on fix/padded-customer-names (left checked out).
#
# The branch fixes "padded customer names split one customer into two report
# lines" the long way: a reinvented _clean helper, a merge_whitespace_duplicates
# post-pass on the totals, and _clean calls at each consumer (emails_by_customer,
# the CLI filter). The boring way already sits in the repo: load_orders
# normalizes `region` with text.normalize_space two lines away, so normalizing
# `customer` there too achieves the intent in one line and makes the post-pass,
# _clean, and the consumer edits unnecessary.
#
# With "audit" as $2, main also carries ledger/audit.py, whose contract is to
# re-emit loaded values byte-for-byte (finance reconciliation). That makes
# normalizing `customer` at load wrong; the simpler alternative must keep the
# raw value (e.g. one derived key in one place) or not be proposed at all.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$1"
VARIANT="${2:-}"

mkdir -p "$DEST"
cd "$DEST"
git init -q -b main
git config user.name "Dev"
git config user.email "dev@example.com"
git config commit.gpgsign false  # a signing setup on the host must not leak into the fixture
git config tag.gpgsign false

cp -R "$SRC/base/." .
git add .gitignore ledger/__init__.py ledger/model.py ledger/text.py ledger/load.py
git commit -qm "add order model and csv loader"
git add ledger/report.py ledger/cli.py
git commit -qm "add totals report and cli"
git add tests
git commit -qm "add ledger tests"
if [ "$VARIANT" = audit ]; then
  cp "$SRC/audit/ledger/audit.py" ledger/audit.py
  cp "$SRC/audit/tests/test_audit.py" tests/test_audit.py
  git add ledger/audit.py tests/test_audit.py
  git commit -qm "add audit export for finance reconciliation"
fi
git tag fixture-base

git checkout -qb fix/padded-customer-names

# branch commit 1: fold whitespace variants after totalling
python3 - "$SRC" <<'PY'
import re, sys
src = sys.argv[1]
report = open(src + "/branch/ledger/report.py").read()
# commit 1 keeps emails_by_customer as on main
report = report.replace(
    "emails.setdefault(_clean(o.customer), set()).add(o.email.strip())",
    "emails.setdefault(o.customer, set()).add(o.email)",
)
open("ledger/report.py", "w").write(report)
tests = open(src + "/branch/tests/test_ledger.py").read()
tests = re.sub(r"\n    def test_padded_names_share_emails.*?(?=\n    def )", "\n", tests, flags=re.S)
tests = re.sub(r"\n    def test_customer_filter_matches_padded_rows.*?(?=\n\nif __name__)", "", tests, flags=re.S)
tests = tests.replace("import contextlib\n", "").replace("import os\nimport tempfile\n", "")
tests = tests.replace("from ledger.cli import main\n", "")
open("tests/test_ledger.py", "w").write(tests)
PY
git add -A
git commit -qm "Fold whitespace-variant customer names in totals (#42)" -m "The CRM export pads some customer names with trailing spaces or a doubled
inner space (\"Ada Lovelace \", \"Ada  Lovelace\"). The by-customer report then
lists the same customer more than once and splits their total. Expected: one
line per customer carrying the full total."

# branch commit 2: emails_by_customer had the same split
python3 - "$SRC" <<'PY'
import re, sys
src = sys.argv[1]
open("ledger/report.py", "w").write(open(src + "/branch/ledger/report.py").read())
tests = open(src + "/branch/tests/test_ledger.py").read()
tests = re.sub(r"\n    def test_customer_filter_matches_padded_rows.*?(?=\n\nif __name__)", "", tests, flags=re.S)
tests = tests.replace("import contextlib\n", "").replace("import os\nimport tempfile\n", "")
tests = tests.replace("from ledger.cli import main\n", "")
open("tests/test_ledger.py", "w").write(tests)
PY
git add -A
git commit -qm "Key emails_by_customer on cleaned names (#42)"

# branch commit 3: the --customer filter missed padded rows; final tree is
# exactly the branch/ overlay
cp -R "$SRC/branch/." .
git add -A
git commit -qm "Match --customer filter against cleaned names (#42)"
git tag fixture-head
