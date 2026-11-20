import io
import unittest

from ledger.load import load_orders, parse_amount
from ledger.report import emails_by_customer, format_totals, totals_by_customer, totals_by_region

CSV = (
    "order_id,customer,email,region,amount\n"
    "1,Ada Lovelace,ada@example.com,EU West,10.50\n"
    "2,Alan Turing,alan@example.com,EU  West ,4.00\n"
    "3,Ada Lovelace,ada@example.com,US East,1.25\n"
)


class TestLoad(unittest.TestCase):
    def test_parse_amount(self):
        self.assertEqual(parse_amount("10.5"), 1050)
        self.assertEqual(parse_amount("3"), 300)

    def test_region_whitespace_normalized(self):
        orders = load_orders(io.StringIO(CSV))
        self.assertEqual([o.region for o in orders], ["EU West", "EU West", "US East"])


class TestReport(unittest.TestCase):
    def setUp(self):
        self.orders = load_orders(io.StringIO(CSV))

    def test_totals_by_customer(self):
        self.assertEqual(
            totals_by_customer(self.orders), {"Ada Lovelace": 1175, "Alan Turing": 400}
        )

    def test_totals_by_region(self):
        self.assertEqual(totals_by_region(self.orders), {"EU West": 1450, "US East": 125})

    def test_emails_by_customer(self):
        self.assertEqual(emails_by_customer(self.orders)["Ada Lovelace"], {"ada@example.com"})

    def test_format_totals(self):
        self.assertEqual(format_totals({"b": 5, "a": 1234}), ["a: 12.34", "b: 0.05"])


if __name__ == "__main__":
    unittest.main()
