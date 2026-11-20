import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from invsvc.store import Store


class StoreRoundTrip(unittest.TestCase):
    def test_append_and_read_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(os.path.join(tmp, "records.jsonl"))
            off_a = store.append({"sku": "A-1", "name": "Widget", "qty": 3})
            off_b = store.append({"sku": "B-2", "name": "Gadget", "qty": 5})
            self.assertEqual(store.read_at(off_a)["sku"], "A-1")
            self.assertEqual(store.read_at(off_b)["qty"], 5)

    def test_iter_with_offsets(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(os.path.join(tmp, "records.jsonl"))
            store.append({"sku": "A-1", "name": "Widget", "qty": 3})
            store.append({"sku": "B-2", "name": "Gadget", "qty": 5})
            rows = list(store.iter_with_offsets())
            self.assertEqual(len(rows), 2)
            for offset, record in rows:
                self.assertEqual(store.read_at(offset), record)


if __name__ == "__main__":
    unittest.main()
