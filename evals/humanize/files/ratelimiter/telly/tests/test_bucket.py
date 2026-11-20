import json
import os
import tempfile
import unittest

from ratelimit.bucket import TokenBucket
from ratelimit.config import load_cfg
from ratelimit.middleware import check, check_burst, parse_client


class BucketTest(unittest.TestCase):
    def test_allows_within_cap(self):
        b = TokenBucket(rate=1.0, cap=2)
        self.assertTrue(b.allow("k", now=0.0))
        self.assertTrue(b.allow("k", now=0.0))

    def test_denies_when_empty(self):
        b = TokenBucket(rate=1.0, cap=1)
        self.assertTrue(b.allow("k", now=0.0))
        self.assertFalse(b.allow("k", now=0.0))

    def test_refills_over_time(self):
        b = TokenBucket(rate=1.0, cap=1)
        b.allow("k", now=0.0)
        self.assertTrue(b.allow("k", now=2.0))


class MiddlewareTest(unittest.TestCase):
    def test_parse_client_known_ip(self):
        self.assertEqual(parse_client({"client_ip": " 10.0.0.1 "}), "10.0.0.1")

    def test_parse_client_missing_maps_to_unknown(self):
        self.assertEqual(parse_client({}), "unknown")
        self.assertEqual(parse_client({"client_ip": None}), "unknown")

    def test_check_uses_client_key(self):
        b = TokenBucket(rate=1.0, cap=1)
        self.assertTrue(check({"client_ip": "1.2.3.4"}, b))


class BurstTest(unittest.TestCase):
    # Test that burst works correctly
    def test_burst_allows_within_cap(self):
        # create a bucket with capacity 5
        b = TokenBucket(rate=1.0, cap=5)
        self.assertTrue(check_burst({"client_ip": "1.2.3.4"}, b, 3))

    def test_burst_denies_beyond_cap(self):
        b = TokenBucket(rate=0.0, cap=2)
        self.assertFalse(check_burst({"client_ip": "1.2.3.4"}, b, 3))


class ConfigTest(unittest.TestCase):
    def test_load_cfg_merges_defaults(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump({"rate": 2.0}, f)
        try:
            cfg = load_cfg(path)
            self.assertEqual(cfg["rate"], 2.0)
            self.assertEqual(cfg["cap"], 10)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
