import hashlib
import hmac


def verify_signature(payload: bytes, sig: str, secret: bytes) -> bool:
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
