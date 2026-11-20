"""Command-line interface for the ledger library.

Other teams script against this surface; keep it stable.
"""

import argparse
import sys
from decimal import Decimal, InvalidOperation

from ledger import accounts, statement, store


def _parse_amount(text):
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise SystemExit(f"invalid amount: {text}")
    if value <= 0:
        raise SystemExit(f"amount must be positive: {text}")
    if value != value.quantize(Decimal("0.01")):
        raise SystemExit(f"amount must have at most two decimal places: {text}")
    return value


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--db", default="ledger.json", help="path to the ledger database file"
    )

    parser = argparse.ArgumentParser(prog="ledger", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("apply", parents=[common], help="apply a credit to an account")
    p.add_argument("--account", required=True)
    p.add_argument("--amount", required=True)

    p = sub.add_parser(
        "charge", parents=[common], help="record a charge against an account"
    )
    p.add_argument("--account", required=True)
    p.add_argument("--amount", required=True)

    p = sub.add_parser("balance", parents=[common], help="print an account balance")
    p.add_argument("--account", required=True)

    p = sub.add_parser(
        "statement", parents=[common], help="print an account statement"
    )
    p.add_argument("--account", required=True)

    p = sub.add_parser(
        "history", parents=[common], help="list an account's transactions"
    )
    p.add_argument("--account", required=True)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    data = store.load(args.db)

    if args.command == "apply":
        accounts.apply_credit(data, args.account, _parse_amount(args.amount))
        store.save(args.db, data)
        print(f"credited {args.amount} to {args.account}")
    elif args.command == "charge":
        accounts.apply_charge(data, args.account, _parse_amount(args.amount))
        store.save(args.db, data)
        print(f"charged {args.amount} to {args.account}")
    elif args.command == "balance":
        print(accounts.balance(data, args.account))
    elif args.command == "statement":
        print(statement.render(data, args.account))
    elif args.command == "history":
        for line in accounts.history(data, args.account):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
