import hashlib
import hmac
import json
import unittest

from paygate.webhook import BadSignature, handle

SECRET = b"whsec_test"


def sign(payload):
    return hmac.new(SECRET, payload, hashlib.sha256).hexdigest()


class HandleTest(unittest.TestCase):
    def test_rejects_bad_signature(self):
        with self.assertRaises(BadSignature):
            handle(b"{}", "nope", SECRET)

    def test_ping(self):
        payload = json.dumps({"type": "ping"}).encode()
        self.assertEqual(handle(payload, sign(payload), SECRET), "pong")

    def test_charge_created(self):
        payload = json.dumps({
            "type": "charge.created", "id": "evt_1",
            "account": {"id": "a1"}, "qty": 2, "price_cents": 500,
        }).encode()
        self.assertEqual(handle(payload, sign(payload), SECRET), 1000)


if __name__ == "__main__":
    unittest.main()
