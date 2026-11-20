"""Account statement rendering."""

from decimal import Decimal

from ledger import accounts, credit


def render(data, name):
    acct = accounts.get_account(data, name)
    lines = [f"statement for {name}", "-" * 24]
    for txn in acct["transactions"]:
        amount = Decimal(txn["amount"])
        if txn["type"] == "charge":
            amount = -amount
        lines.append(f"{txn['type']:<8}{amount:>12}")
    bonus = credit.total_bonus(accounts.credit_amounts(data, name))
    lines.append(f"{'bonus':<8}{bonus:>12}")
    lines.append("-" * 24)
    lines.append(f"{'total':<8}{accounts.balance(data, name):>12}")
    return "\n".join(lines)
