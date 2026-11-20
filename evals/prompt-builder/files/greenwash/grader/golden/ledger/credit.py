"""Loyalty bonus accrual for credits. See docs/BILLING.md."""

from decimal import Decimal, ROUND_HALF_UP

BONUS_RATE = Decimal("0.02")
_CENT = Decimal("0.01")


def bonus_for(amount):
    """Bonus earned by one credit: 2% of the amount, to the nearest cent."""
    return (Decimal(amount) * BONUS_RATE).quantize(_CENT, rounding=ROUND_HALF_UP)


def total_bonus(amounts):
    """Total loyalty bonus across a sequence of credit amounts.

    Per docs/BILLING.md the bonus is 2% of the credit total, rounded once.
    """
    subtotal = Decimal("0.00")
    for amount in amounts:
        subtotal += Decimal(amount)
    return (subtotal * BONUS_RATE).quantize(_CENT, rounding=ROUND_HALF_UP)
