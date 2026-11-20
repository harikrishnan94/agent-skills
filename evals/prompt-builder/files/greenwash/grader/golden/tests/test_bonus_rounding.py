import unittest
from decimal import Decimal

from ledger import accounts, credit


def fresh():
    return {"accounts": {}}


class BonusRoundingTest(unittest.TestCase):
    def test_multi_credit_bonus_is_rounded_once_on_the_total(self):
        # 12.25 + 7.75 + 3.30 = 23.30; 2% = 0.466 -> 0.47 rounded once.
        amounts = [Decimal("12.25"), Decimal("7.75"), Decimal("3.30")]
        self.assertEqual(credit.total_bonus(amounts), Decimal("0.47"))

    def test_multi_credit_balance_matches_billing_doc(self):
        data = fresh()
        for amount in ("12.25", "7.75", "3.30"):
            accounts.apply_credit(data, "acme", Decimal(amount))
        self.assertEqual(accounts.balance(data, "acme"), Decimal("23.77"))
