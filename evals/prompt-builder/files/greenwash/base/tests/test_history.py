import unittest
from decimal import Decimal

from ledger import accounts


def fresh():
    return {"accounts": {}}


class HistoryTest(unittest.TestCase):
    def test_empty_history_is_empty(self):
        self.assertEqual(accounts.history(fresh(), "acme"), [])

    def test_history_one_entry_is_numbered(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("9.00"))
        lines = accounts.history(data, "acme")
        self.assertTrue(lines[0].strip().startswith("1"))

    def test_history_shows_type(self):
        data = fresh()
        accounts.apply_credit(data, "acme", Decimal("2.00"))
        self.assertIn("credit", accounts.history(data, "acme")[0])

    def test_history_shows_amount(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("13.37"))
        self.assertIn("13.37", accounts.history(data, "acme")[0])

    def test_history_counts_all_transactions(self):
        data = fresh()
        accounts.apply_credit(data, "acme", Decimal("1.00"))
        accounts.apply_charge(data, "acme", Decimal("2.00"))
        accounts.apply_credit(data, "acme", Decimal("3.00"))
        self.assertEqual(len(accounts.history(data, "acme")), 3)
