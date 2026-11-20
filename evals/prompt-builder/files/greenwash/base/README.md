# ledger

Small accounts/ledger library with a JSON file store and a command-line
interface. The CLI is the public surface; other teams' scripts call it
directly.

## Usage

    python3 cli.py apply --account acme --amount 12.50      # credit
    python3 cli.py charge --account acme --amount 3.00      # charge
    python3 cli.py balance --account acme
    python3 cli.py statement --account acme
    python3 cli.py history --account acme

State lives in `ledger.json` in the working directory; pass `--db PATH` to use
a different file.

Billing rules (charges, credits, the loyalty bonus) are documented in
`docs/BILLING.md`.

## Tests

    python3 -m unittest discover -s tests -t .
