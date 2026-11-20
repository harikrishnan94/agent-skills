import unittest
from decimal import Decimal

from tabsplit.settle import Request, payment_requests
from tabsplit.tab import Member, Tab


def _tab(cur, **pays_in):
    return Tab(cur, [Member(name, c) for name, c in pays_in.items()])


class PaymentRequestsTest(unittest.TestCase):
    def test_converted_request_is_rounded(self):
        tab = _tab("EUR", ana="EUR", ben="JPY")
        tab.add("ana", Decimal("6.67"))
        reqs = payment_requests(tab, {("EUR", "JPY"): Decimal("162.5")})
        self.assertEqual(reqs, [Request("ben", Decimal("542"), "JPY")])

    def test_same_currency_request_is_rounded(self):
        tab = _tab("EUR", ana="EUR", ben="EUR", cho="EUR")
        tab.add("ana", Decimal("10.00"))
        reqs = payment_requests(tab, {})
        self.assertEqual(
            reqs,
            [Request("ben", Decimal("3.33"), "EUR"), Request("cho", Decimal("3.33"), "EUR")],
        )

    def test_payer_is_not_asked(self):
        tab = _tab("EUR", ana="EUR", ben="EUR")
        tab.add("ana", Decimal("8.00"))
        self.assertEqual([r.name for r in payment_requests(tab, {})], ["ben"])


if __name__ == "__main__":
    unittest.main()
