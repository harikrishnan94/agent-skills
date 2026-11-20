import unittest

from src.parser import parse


class ParseTest(unittest.TestCase):
    def test_parses_pairs(self):
        self.assertEqual(parse("a=1\nb = two"), {"a": "1", "b": "two"})

    def test_value_may_contain_equals(self):
        self.assertEqual(parse("url=http://x/?q=1"), {"url": "http://x/?q=1"})

    def test_skips_blank_lines_and_comments(self):
        self.assertEqual(parse("a=1\n\n# note\nb=2"), {"a": "1", "b": "2"})


if __name__ == "__main__":
    unittest.main()
