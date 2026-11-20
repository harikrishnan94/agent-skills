"""Retry handling for declined charges."""

from dataclasses import dataclass

from .billing import ChargeDeclined, charge

PENDING = "pending"
RETRYING = "retrying"
DEAD = "dead"

BASE_DELAY = 2.0
MAX_ATTEMPTS = 12
# attempts is persisted with the event and keeps climbing toward MAX_ATTEMPTS
# across worker restarts; uncapped, 2 ** 12 puts the next retry hours out.
# cap the exponent, not the counter.
MAX_BACKOFF_EXP = 6


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
        return (self.attempts, self.status)

    @classmethod
    def from_row(cls, event_id, row):
        return cls(event_id=event_id, attempts=int(row[0]), status=row[1])


def next_delay(attempts: int) -> float:
    exp = min(attempts, MAX_BACKOFF_EXP)
    return BASE_DELAY * 2 ** exp


def retry_charge(state: RetryState, account, qty, price_cents):
    if state.status == DEAD:
        return None
    try:
        return charge(account, qty, price_cents)
    except ChargeDeclined:
        state.record_failure()
        return None
