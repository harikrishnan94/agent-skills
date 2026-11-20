"""Inventory service command-line interface."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from invsvc.index import load_index
from invsvc.store import Store

ROOT = os.path.dirname(os.path.abspath(__file__))
RECORDS = os.path.join(ROOT, "data", "records.jsonl")
INDEX = os.path.join(ROOT, "data", "index.bin")


class InventoryService:
    """Loads the search index at startup; all reads go through it."""

    def __init__(self, records_path=RECORDS, index_path=INDEX):
        self.store = Store(records_path)
        self.index_path = index_path
        self.index = load_index(index_path)

    def list_records(self):
        for sku in sorted(self.index):
            yield self.store.read_at(self.index[sku])

    def get(self, sku):
        if sku not in self.index:
            return None
        return self.store.read_at(self.index[sku])


def cmd_list(args):
    svc = InventoryService()
    for rec in svc.list_records():
        print("%s\t%s\t%d" % (rec["sku"], rec["name"], rec["qty"]))
    return 0


def cmd_get(args):
    svc = InventoryService()
    rec = svc.get(args.sku)
    if rec is None:
        print("not found: %s" % args.sku, file=sys.stderr)
        return 1
    print("%s\t%s\t%d" % (rec["sku"], rec["name"], rec["qty"]))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="cli.py", description="inventory service")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list all records")
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="look up one record by sku")
    p_get.add_argument("--sku", required=True)
    p_get.set_defaults(func=cmd_get)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
