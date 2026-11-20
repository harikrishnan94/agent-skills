import os
import tempfile
import unittest

from taskq import store


class StoreTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_add_assigns_ids(self):
        a = store.add("one", path=self.path)
        b = store.add("two", path=self.path)
        self.assertEqual((a["id"], b["id"]), (1, 2))

    def test_add_sets_due_from_hours(self):
        rec = store.add("t", due_h=2, path=self.path)
        self.assertEqual(rec["due"], rec["ts"] + 7200)

    def test_ls_sorted_by_ts(self):
        store.add("a", path=self.path)
        store.add("b", path=self.path)
        recs = store.ls(path=self.path)
        self.assertEqual([r["ts"] for r in recs], sorted(r["ts"] for r in recs))

    def test_done_marks_record(self):
        rec = store.add("t", path=self.path)
        self.assertTrue(store.done(rec["id"], path=self.path)["done"])

    def test_done_missing_returns_none(self):
        self.assertIsNone(store.done(99, path=self.path))


if __name__ == "__main__":
    unittest.main()
