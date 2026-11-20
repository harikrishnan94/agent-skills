from collections import namedtuple

from .money import to_minor

Request = namedtuple("Request", "name amount cur")


def request_amount(balance, tab_cur, pay_cur, rates):
    """The amount to ask a member for, in the currency the member pays in."""
    if pay_cur != tab_cur:
        rate = rates[tab_cur, pay_cur]
        amount = to_minor(balance * rate, pay_cur)
    else:
        amount = balance
    return amount


def payment_requests(tab, rates):
    """One Request per member who owes the group."""
    out = []
    for m in tab.members:
        balance = tab.balance(m.name)
        if balance <= 0:
            continue
        amount = request_amount(balance, tab.cur, m.pays_in, rates)
        out.append(Request(m.name, amount, m.pays_in))
    return out
