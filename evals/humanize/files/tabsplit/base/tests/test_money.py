import unittest
from decimal import Decimal

from tabsplit.money import to_minor


class ToMinorTest(unittest.TestCase):
    def test_two_digits_by_default(self):
        self.assertEqual(to_minor(Decimal("3.3333"), "EUR"), Decimal("3.33"))

    def test_listed_currencies(self):
        self.assertEqual(to_minor(Decimal("541.66"), "JPY"), Decimal("542"))
        self.assertEqual(to_minor(Decimal("1.02349"), "KWD"), Decimal("1.023"))

    def test_half_goes_to_even(self):
        self.assertEqual(to_minor(Decimal("0.125"), "EUR"), Decimal("0.12"))
        self.assertEqual(to_minor(Decimal("0.135"), "EUR"), Decimal("0.14"))


if __name__ == "__main__":
    unittest.main()
