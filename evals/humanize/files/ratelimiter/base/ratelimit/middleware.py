"""Request-side helpers.

client_ip may be absent or None behind some proxies; parse_client maps
those to "unknown" so limits still apply via the shared bucket key.
"""


def parse_client(req):
    ip = req.get("client_ip")
    if ip is None:
        return "unknown"
    return ip.strip() or "unknown"


def check(req, bucket):
    return bucket.allow(parse_client(req))
