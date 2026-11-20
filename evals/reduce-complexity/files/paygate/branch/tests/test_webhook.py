import hashlib
import hmac
import json
import unittest

from paygate.retry import MAX_ATTEMPTS
from paygate.webhook import BadSignature, handle, process_event

SECRET = b"whsec_test"


def sign(payload):
    return hmac.new(SECRET, payload, hashlib.sha256).hexdigest()


def charge_evt(**over):
    evt = {"type": "charge.created", "id": "evt_1",
           "account": {"id": "a1"}, "qty": 2, "price_cents": 500}
    evt.update(over)
    return json.dumps(evt).encode()


class HandleTest(unittest.TestCase):
    def test_rejects_bad_signature(self):
        with self.assertRaises(BadSignature):
            handle(b"{}", "nope", SECRET)

    def test_ping(self):
        payload = json.dumps({"type": "ping"}).encode()
        self.assertEqual(handle(payload, sign(payload), SECRET), "pong")

    def test_charge_created(self):
        payload = charge_evt()
        self.assertEqual(handle(payload, sign(payload), SECRET), 1000)


class ProcessEventTest(unittest.TestCase):
    def test_rejects_tampered_payload(self):
        payload = charge_evt()
        sig = sign(payload)
        with self.assertRaises(BadSignature):
            process_event(charge_evt(qty=9), sig, SECRET)

    def test_declined_charge_schedules_retry(self):
        payload = charge_evt(account={"id": "a1", "blocked": True})
        out = process_event(payload, sign(payload), SECRET)
        self.assertEqual(out["retry_in"], 4.0)
        self.assertEqual(out["state"], (1, "retrying"))

    def test_retry_event_resumes_stored_state(self):
        payload = charge_evt(type="charge.retry",
                             account={"id": "a1", "blocked": True},
                             state=[3, "retrying"])
        out = handle(payload, sign(payload), SECRET)
        self.assertEqual(out["state"], (4, "retrying"))
        self.assertEqual(out["retry_in"], 32.0)

    def test_dead_letter_after_max_attempts(self):
        payload = charge_evt(type="charge.retry",
                             account={"id": "a1", "blocked": True},
                             state=[MAX_ATTEMPTS - 1, "retrying"])
        self.assertIsNone(process_event(payload, sign(payload), SECRET))


if __name__ == "__main__":
    unittest.main()
