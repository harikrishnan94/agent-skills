#!/bin/bash
# Build the paygate fixture repo at $1: base history on main, then the retry
# work built up over four commits on feature/retry-processing. Intermediate
# commit states live in the heredocs below; the last commit applies branch/
# wholesale so the final tree exactly matches that directory.
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
git add .gitignore paygate/__init__.py paygate/signature.py
git commit -qm "add webhook signature verification"
git add paygate/billing.py paygate/webhook.py
git commit -qm "add billing and webhook dispatch"
git add tests
git commit -qm "add billing and webhook tests"
git tag fixture-base

git checkout -qb feature/retry-processing

cat > paygate/retry.py <<'EOF'
"""Retry handling for declined charges."""

from .billing import ChargeDeclined, charge

MAX_ATTEMPTS = 12


def retry_charge(event_id, attempts, account, qty, price_cents):
    """Returns (total, attempts); total is None while the charge is declined."""
    if attempts >= MAX_ATTEMPTS:
        return None, attempts
    try:
        return charge(account, qty, price_cents), attempts
    except ChargeDeclined:
        return None, attempts + 1
EOF
cat > tests/test_retry.py <<'EOF'
import unittest

from paygate.retry import MAX_ATTEMPTS, retry_charge

BLOCKED = {"id": "a1", "blocked": True}


class RetryChargeTest(unittest.TestCase):
    def test_success_leaves_attempts(self):
        total, attempts = retry_charge("evt_1", 2, {"id": "a1"}, 1, 300)
        self.assertEqual((total, attempts), (300, 2))

    def test_declined_increments(self):
        total, attempts = retry_charge("evt_1", 0, dict(BLOCKED), 1, 300)
        self.assertEqual((total, attempts), (None, 1))

    def test_gives_up_at_max(self):
        total, attempts = retry_charge("evt_1", MAX_ATTEMPTS, {"id": "a1"}, 1, 300)
        self.assertEqual((total, attempts), (None, MAX_ATTEMPTS))


if __name__ == "__main__":
    unittest.main()
EOF
git add paygate/retry.py tests/test_retry.py
git commit -qm "add retry for declined charges"

cp "$SRC/branch/REVIEW.md" REVIEW.md
cat > paygate/retry.py <<'EOF'
"""Retry handling for declined charges."""

from dataclasses import dataclass

from .billing import ChargeDeclined, charge

PENDING = "pending"
RETRYING = "retrying"
DEAD = "dead"

MAX_ATTEMPTS = 12


@dataclass
class RetryState:
    event_id: str
    attempts: int = 0
    status: str = PENDING

    def record_failure(self):
        if self.status == DEAD:
            raise ValueError("dead event cannot re-enter retry: %s" % self.event_id)
        self.status = RETRYING
        self.attempts += 1
        if self.attempts >= MAX_ATTEMPTS:
            self.status = DEAD

    def to_row(self):
        return (self.event_id, self.attempts, self.status)

    @classmethod
    def from_row(cls, row):
        return cls(event_id=row[0], attempts=int(row[1]), status=row[2])


def retry_charge(state: RetryState, account, qty, price_cents):
    if state.status == DEAD:
        return None
    try:
        return charge(account, qty, price_cents)
    except ChargeDeclined:
        state.record_failure()
        return None
EOF
cat > tests/test_retry.py <<'EOF'
import unittest

from paygate.retry import (
    DEAD, MAX_ATTEMPTS, PENDING, RETRYING, RetryState, retry_charge,
)

BLOCKED = {"id": "a1", "blocked": True}


class RetryChargeTest(unittest.TestCase):
    def test_success_returns_total(self):
        state = RetryState(event_id="evt_1")
        self.assertEqual(retry_charge(state, {"id": "a1"}, 2, 300), 600)
        self.assertEqual(state.status, PENDING)

    def test_declined_marks_retrying(self):
        state = RetryState(event_id="evt_1")
        self.assertIsNone(retry_charge(state, dict(BLOCKED), 1, 300))
        self.assertEqual((state.status, state.attempts), (RETRYING, 1))

    def test_dead_letter_at_max_attempts(self):
        state = RetryState(event_id="evt_1", attempts=MAX_ATTEMPTS - 1)
        retry_charge(state, dict(BLOCKED), 1, 300)
        self.assertEqual(state.status, DEAD)

    def test_dead_state_never_reenters(self):
        state = RetryState(event_id="evt_1", status=DEAD)
        self.assertIsNone(retry_charge(state, {"id": "a1"}, 1, 300))
        with self.assertRaises(ValueError):
            state.record_failure()

    def test_row_round_trip(self):
        state = RetryState(event_id="evt_1", attempts=4, status=RETRYING)
        self.assertEqual(RetryState.from_row(state.to_row()), state)


if __name__ == "__main__":
    unittest.main()
EOF
git add REVIEW.md paygate/retry.py tests/test_retry.py
git commit -qm "make retry states explicit per review"

cp "$SRC/branch/paygate/retry.py" paygate/retry.py
cp "$SRC/branch/tests/test_retry.py" tests/test_retry.py
git add paygate/retry.py tests/test_retry.py
git commit -qm "add capped backoff for stored attempts"

cp -R "$SRC/branch/." .
git add -A
git commit -qm "re-verify signature in retry processing"
git tag fixture-head
