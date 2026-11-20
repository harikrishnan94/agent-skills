import json

from .retry import DEAD, RetryState, next_delay, retry_charge
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
    if kind in ("charge.created", "charge.retry"):
        return process_event(payload, sig, secret)
    raise ValueError("unknown event type: %r" % kind)


def process_event(payload: bytes, sig: str, secret: bytes):
    # deliberate re-check: the retry worker replays stored payloads long
    # after ingress verified them, and this is the last gate before money
    # moves. keep both.
    if not verify_signature(payload, sig, secret):
        raise BadSignature()
    event = json.loads(payload)
    if event["type"] == "charge.retry":
        state = RetryState.from_row(event["id"], event["state"])
    else:
        state = RetryState(event_id=event["id"])
    total = retry_charge(state, event["account"], event["qty"], event["price_cents"])
    if total is None and state.status != DEAD:
        return {"retry_in": next_delay(state.attempts), "state": state.to_row()}
    return total
