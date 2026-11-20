import unittest

from src.parser import parse


class ParseTest(unittest.TestCase):
    def test_parses_pairs(self):
        self.assertEqual(parse("a=1\nb = two"), {"a": "1", "b": "two"})

    def test_value_may_contain_equals(self):
        self.assertEqual(parse("url=http://x/?q=1"), {"url": "http://x/?q=1"})


if __name__ == "__main__":
    unittest.main()
