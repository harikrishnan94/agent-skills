from decimal import ROUND_HALF_EVEN, Decimal

# ISO 4217 minor-unit digits; a currency not listed here has 2.
MINOR_DIGITS = {"JPY": 0, "KWD": 3}


def to_minor(amount, cur):
    """Round `amount` to the smallest unit a bank moves in `cur`.

    A bank cannot move a fraction of a minor unit: it rejects a request
    for 3.3333 EUR, and a payment of 3.33 never matches one.
    """
    step = Decimal(1).scaleb(-MINOR_DIGITS.get(cur, 2))
    return amount.quantize(step, rounding=ROUND_HALF_EVEN)
