import unittest
from decimal import Decimal

from ledger import accounts


def fresh():
    return {"accounts": {}}


class AccountBasicsTest(unittest.TestCase):
    def test_new_account_balance_is_zero(self):
        self.assertEqual(accounts.balance(fresh(), "nobody"), Decimal("0.00"))

    def test_get_account_missing_returns_empty(self):
        acct = accounts.get_account(fresh(), "ghost")
        self.assertEqual(acct["transactions"], [])

    def test_apply_credit_records_transaction(self):
        data = fresh()
        accounts.apply_credit(data, "acme", Decimal("10.00"))
        txns = data["accounts"]["acme"]["transactions"]
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0]["type"], "credit")

    def test_apply_charge_records_transaction(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("4.50"))
        txns = data["accounts"]["acme"]["transactions"]
        self.assertEqual(txns[0], {"type": "charge", "amount": "4.50"})

    def test_amounts_stored_as_strings(self):
        data = fresh()
        accounts.apply_credit(data, "acme", Decimal("19.99"))
        stored = data["accounts"]["acme"]["transactions"][0]["amount"]
        self.assertIsInstance(stored, str)
        self.assertEqual(stored, "19.99")

    def test_accounts_are_isolated(self):
        data = fresh()
        accounts.apply_charge(data, "a", Decimal("5.00"))
        self.assertEqual(accounts.balance(data, "b"), Decimal("0.00"))

    def test_balance_returns_decimal(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("1.00"))
        self.assertIsInstance(accounts.balance(data, "acme"), Decimal)

    def test_credit_amounts_lists_only_credits(self):
        data = fresh()
        accounts.apply_credit(data, "acme", Decimal("3.00"))
        accounts.apply_charge(data, "acme", Decimal("1.00"))
        self.assertEqual(accounts.credit_amounts(data, "acme"), [Decimal("3.00")])
