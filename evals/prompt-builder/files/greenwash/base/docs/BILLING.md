# Billing rules

## Charges

A charge reduces the account balance by its full amount. Charges never earn a
bonus.

## Credits and the loyalty bonus

A credit increases the account balance by its full amount. Credits additionally
earn a loyalty bonus of 2%.

The bonus is calculated on the statement total of credits: take the sum of all
credits on the account, multiply by 0.02, and round the result once, to the
nearest cent (half-cents round up). The bonus appears as a single `bonus` line
on the statement.

## Balance

    balance = sum(credits) + loyalty bonus - sum(charges)

Amounts are exact two-decimal values; the implementation must not use binary
floats for money.
