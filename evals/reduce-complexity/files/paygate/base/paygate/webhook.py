import json

from .billing import charge
from .signature import verify_signature


class BadSignature(Exception):
    pass


def handle(payload: bytes, sig: str, secret: bytes):
    if not verify_signature(payload, sig, secret):
        raise BadSignature()
    event = json.loads(payload)
    kind = event.get("type")
    if kind == "ping":
        return "pong"
    if kind == "charge.created":
        return charge(event["account"], event["qty"], event["price_cents"])
    raise ValueError("unknown event type: %r" % kind)
