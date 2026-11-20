import unittest
from decimal import Decimal

from ledger import accounts, statement


def fresh():
    return {"accounts": {}}


def total_line(text):
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == "total":
            return Decimal(parts[-1])
    raise AssertionError("no total line in statement")


class StatementTest(unittest.TestCase):
    def test_statement_names_account(self):
        text = statement.render(fresh(), "acme")
        self.assertIn("statement for acme", text)

    def test_empty_account_total_is_zero(self):
        text = statement.render(fresh(), "acme")
        self.assertEqual(total_line(text), Decimal("0.00"))

    def test_charge_only_statement(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("25.00"))
        text = statement.render(data, "acme")
        self.assertIn("charge", text)
        self.assertIn("-25.00", text)
        self.assertEqual(total_line(text), Decimal("-25.00"))

    def test_transactions_listed_in_order(self):
        data = fresh()
        accounts.apply_charge(data, "acme", Decimal("1.23"))
        accounts.apply_charge(data, "acme", Decimal("4.56"))
        text = statement.render(data, "acme")
        self.assertLess(text.index("1.23"), text.index("4.56"))

    def test_statement_has_bonus_line(self):
        data = fresh()
        accounts.apply_credit(data, "acme", Decimal("10.00"))
        lines = statement.render(data, "acme").splitlines()
        self.assertTrue(any(line.startswith("bonus") for line in lines))

    def test_statement_total_matches_balance(self):
        data = fresh()
        accounts.apply_credit(data, "acme", Decimal("30.00"))
        accounts.apply_charge(data, "acme", Decimal("12.34"))
        text = statement.render(data, "acme")
        self.assertEqual(total_line(text), accounts.balance(data, "acme"))
