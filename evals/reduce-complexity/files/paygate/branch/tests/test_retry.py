import unittest

from paygate.retry import (
    BASE_DELAY, DEAD, MAX_ATTEMPTS, MAX_BACKOFF_EXP, PENDING, RETRYING,
    RetryState, next_delay, retry_charge,
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
        self.assertEqual(RetryState.from_row("evt_1", state.to_row()), state)


class BackoffTest(unittest.TestCase):
    def test_delay_doubles_below_cap(self):
        self.assertEqual(next_delay(3), BASE_DELAY * 8)

    def test_delay_flat_past_cap(self):
        self.assertEqual(next_delay(MAX_BACKOFF_EXP + 3),
                         BASE_DELAY * 2 ** MAX_BACKOFF_EXP)


if __name__ == "__main__":
    unittest.main()
