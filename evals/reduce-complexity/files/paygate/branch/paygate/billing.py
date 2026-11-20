class ChargeDeclined(Exception):
    pass


def charge(account, qty, price_cents) -> int:
    if qty <= 0:
        raise ValueError("qty must be positive: %r" % qty)
    if account.get("blocked"):
        raise ChargeDeclined(account.get("id"))
    total = qty * price_cents
    account["charged_cents"] = account.get("charged_cents", 0) + total
    return total
