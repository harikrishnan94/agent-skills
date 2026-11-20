"""Behavior probe for the fix-mode eval: absent/None client_ip must map to the
shared "unknown" bucket key per the middleware docstring contract.

Usage: probe_guard.py <repo>. Never shown to the executor.
"""

import sys


def main(repo):
    sys.path.insert(0, repo)
    from ratelimit.bucket import TokenBucket
    from ratelimit.middleware import check_burst, parse_client

    assert parse_client({}) == "unknown", "parse_client({}) != 'unknown'"
    assert parse_client({"client_ip": None}) == "unknown", "parse_client(None ip) != 'unknown'"

    # rate 0, cap 1: if both anonymous requests share the "unknown" key, the
    # second burst must be denied
    b = TokenBucket(rate=0.0, cap=1)
    r1 = check_burst({"path": "/"}, b, 1)
    r2 = check_burst({"client_ip": None}, b, 1)
    assert r1 is True, "first anonymous burst denied: %r" % r1
    assert r2 is False, "anonymous clients do not share the unknown key: %r" % r2
    print("probe OK")


if __name__ == "__main__":
    main(sys.argv[1])
