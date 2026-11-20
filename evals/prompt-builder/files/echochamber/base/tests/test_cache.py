import unittest

from kvstore.cache import LRUCache


class TestLRUCache(unittest.TestCase):
    def test_hit_after_put(self):
        cache = LRUCache(4)
        cache.put("a", 1)
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.hits, 1)
        self.assertEqual(cache.misses, 0)

    def test_miss_counts(self):
        cache = LRUCache(4)
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.misses, 1)

    def test_evicts_least_recently_used(self):
        cache = LRUCache(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)

    def test_capacity_bound(self):
        cache = LRUCache(3)
        for i in range(10):
            cache.put(str(i), i)
        self.assertEqual(len(cache), 3)


if __name__ == "__main__":
    unittest.main()
