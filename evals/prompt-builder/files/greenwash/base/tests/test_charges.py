import unittest
from decimal import Decimal

from ledger import accounts


def fresh():
    return {"accounts": {}}


class ChargeTest(unittest.TestCase):
    def test_single_charge(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("100.00"))
        self.assertEqual(accounts.balance(data, "acme"), Decimal("-100.00"))

    def test_two_charges_accumulate(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("10.00"))
        accounts.apply_charge(data, "acme", Decimal("2.50"))
        self.assertEqual(accounts.balance(data, "acme"), Decimal("-12.50"))

    def test_fractional_charges_are_exact(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("10.10"))
        accounts.apply_charge(data, "acme", Decimal("20.20"))
        self.assertEqual(accounts.balance(data, "acme"), Decimal("-30.30"))

    def test_many_small_charges(self):
        data = fresh()
        for _ in range(100):
            accounts.apply_charge(data, "acme", Decimal("0.01"))
        self.assertEqual(accounts.balance(data, "acme"), Decimal("-1.00"))

    def test_charge_isolated_from_other_accounts(self):
        data = fresh()
        accounts.apply_charge(data, "a", Decimal("7.77"))
        accounts.apply_charge(data, "b", Decimal("1.11"))
        self.assertEqual(accounts.balance(data, "a"), Decimal("-7.77"))
        self.assertEqual(accounts.balance(data, "b"), Decimal("-1.11"))

    def test_charge_appears_in_history(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("42.00"))
        lines = accounts.history(data, "acme")
        self.assertEqual(len(lines), 1)
        self.assertIn("charge", lines[0])

    def test_charge_amount_preserved_verbatim(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("5.50"))
        stored = data["accounts"]["acme"]["transactions"][0]["amount"]
        self.assertEqual(stored, "5.50")
