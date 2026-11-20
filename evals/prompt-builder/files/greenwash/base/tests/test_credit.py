import unittest
from decimal import Decimal

from ledger import accounts, credit, statement


def fresh():
    return {"accounts": {}}


def bonus_line(text):
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == "bonus":
            return Decimal(parts[-1])
    raise AssertionError("no bonus line in statement")


class CreditBonusTest(unittest.TestCase):
    def test_single_credit_earns_bonus(self):
        data = fresh()
        accounts.apply_credit(data, "acme", Decimal("12.37"))
        expected = Decimal("12.37") + credit.bonus_for(Decimal("12.37"))
        self.assertEqual(accounts.balance(data, "acme"), expected)

    def test_multi_credit_balance_includes_bonus(self):
        data = fresh()
        amounts = [Decimal("10.10"), Decimal("4.20"), Decimal("6.35")]
        for amount in amounts:
            accounts.apply_credit(data, "acme", amount)
        expected = sum(amounts) + credit.total_bonus(amounts)
        self.assertEqual(accounts.balance(data, "acme"), expected)

    def test_statement_bonus_matches_credit_module(self):
        data = fresh()
        amounts = [Decimal("8.15"), Decimal("2.40")]
        for amount in amounts:
            accounts.apply_credit(data, "acme", amount)
        text = statement.render(data, "acme")
        self.assertEqual(bonus_line(text), credit.total_bonus(amounts))

    def test_bonus_never_negative(self):
        for raw in ("0.01", "0.49", "1.00", "99.99"):
            self.assertGreaterEqual(credit.bonus_for(Decimal(raw)), Decimal("0.00"))

    def test_bonus_grows_with_more_credits(self):
        few = credit.total_bonus([Decimal("20.00")])
        more = credit.total_bonus([Decimal("20.00"), Decimal("30.00")])
        self.assertGreater(more, few)

    def test_charges_do_not_earn_bonus(self):
        data = fresh()
        accounts.apply_credit(data, "acme", Decimal("50.00"))
        before = accounts.balance(data, "acme")
        accounts.apply_charge(data, "acme", Decimal("10.00"))
        self.assertEqual(accounts.balance(data, "acme"), before - Decimal("10.00"))

    def test_bonus_has_two_decimal_places(self):
        self.assertEqual(credit.bonus_for(Decimal("12.34")).as_tuple().exponent, -2)
