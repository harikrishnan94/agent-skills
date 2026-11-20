import io
import unittest

from ledger.audit import write_audit
from ledger.load import load_orders

RAW = (
    "order_id,customer,email,region,amount\n"
    "7,Ada Lovelace ,ada@example.com,EU West,1.00\n"
)


class TestAudit(unittest.TestCase):
    def test_audit_keeps_customer_exactly_as_exported(self):
        out = io.StringIO()
        write_audit(load_orders(io.StringIO(RAW)), out)
        self.assertEqual(out.getvalue().splitlines()[1], "7,Ada Lovelace ,ada@example.com,EU West,100")


if __name__ == "__main__":
    unittest.main()
