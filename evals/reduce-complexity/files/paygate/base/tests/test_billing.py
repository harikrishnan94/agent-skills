import unittest

from paygate.billing import ChargeDeclined, charge


class ChargeTest(unittest.TestCase):
    def test_charges_total(self):
        acct = {"id": "a1"}
        self.assertEqual(charge(acct, 3, 250), 750)
        self.assertEqual(acct["charged_cents"], 750)

    def test_rejects_bad_qty(self):
        with self.assertRaises(ValueError):
            charge({"id": "a1"}, 0, 250)

    def test_declined_when_blocked(self):
        with self.assertRaises(ChargeDeclined):
            charge({"id": "a1", "blocked": True}, 1, 100)


if __name__ == "__main__":
    unittest.main()
