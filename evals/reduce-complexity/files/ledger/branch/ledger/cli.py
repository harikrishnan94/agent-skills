import argparse
import sys

from ledger.load import load_orders
from ledger.report import _clean, format_totals, totals_by_customer, totals_by_region


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ledger")
    parser.add_argument("path")
    parser.add_argument("--by", choices=["customer", "region"], default="customer")
    parser.add_argument("--customer")
    args = parser.parse_args(argv)

    with open(args.path, newline="") as f:
        orders = load_orders(f)
    if args.customer:
        orders = [o for o in orders if _clean(o.customer) == _clean(args.customer)]
    totals = totals_by_customer(orders) if args.by == "customer" else totals_by_region(orders)
    for line in format_totals(totals):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
