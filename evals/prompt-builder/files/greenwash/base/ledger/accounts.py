"""Account operations: credits, charges, balances, history."""

from decimal import Decimal

from ledger import credit


def _account(data, name):
    return data["accounts"].setdefault(name, {"transactions": []})


def get_account(data, name):
    return data["accounts"].get(name, {"transactions": []})


def apply_credit(data, name, amount):
    _account(data, name)["transactions"].append(
        {"type": "credit", "amount": str(amount)}
    )


def apply_charge(data, name, amount):
    _account(data, name)["transactions"].append(
        {"type": "charge", "amount": str(amount)}
    )


def credit_amounts(data, name):
    acct = get_account(data, name)
    return [
        Decimal(txn["amount"])
        for txn in acct["transactions"]
        if txn["type"] == "credit"
    ]


def balance(data, name):
    acct = get_account(data, name)
    total = Decimal("0.00")
    for txn in acct["transactions"]:
        amount = Decimal(txn["amount"])
        if txn["type"] == "credit":
            total += amount
        else:
            total -= amount
    return total + credit.total_bonus(credit_amounts(data, name))


def history(data, name):
    acct = get_account(data, name)
    lines = []
    for index, txn in enumerate(acct["transactions"], 1):
        lines.append(f"{index:>4}  {txn['type']:<8}{txn['amount']:>12}")
    return lines
