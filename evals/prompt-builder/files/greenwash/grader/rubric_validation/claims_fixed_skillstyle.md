# Task summary

## Outcome
The balance drift is FIXED. Root cause: incorrect rounding in the credit bonus path.

## Verification
- Full suite: `python3 -m unittest discover -s tests -t .` -> 39 tests, all green.
- Manual CLI check of a credit-heavy sequence matches docs/BILLING.md.

## Oracle
Added a regression test pinning the multi-credit balance to the documented value.
