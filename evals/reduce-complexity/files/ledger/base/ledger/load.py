import csv

from ledger.model import Order
from ledger.text import normalize_space


def parse_amount(text):
    whole, _, frac = text.strip().partition(".")
    return int(whole) * 100 + int((frac + "00")[:2])


def load_orders(fileobj):
    orders = []
    for row in csv.DictReader(fileobj):
        orders.append(
            Order(
                order_id=row["order_id"],
                customer=row["customer"],
                email=row["email"],
                region=normalize_space(row["region"]),
                amount_cents=parse_amount(row["amount"]),
            )
        )
    return orders
