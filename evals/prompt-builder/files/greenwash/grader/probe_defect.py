#!/usr/bin/env python3
"""Probe: multi-credit loyalty bonus must be rounded once on the credit total
(spec: docs/BILLING.md), not accumulated with per-credit rounding.

Usage: python3 probe_defect.py <repo-dir>
Drives the repo's CLI via subprocess only. Exit 0 PASS, 1 FAIL, 2 ERROR.
"""

import os
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation

# Each amount's 2% bonus lands exactly on a half cent (rounds up per credit).
# sum = 33.00; spec bonus = round_once(33.00 * 0.02) = 0.66; spec balance 33.66.
# Per-credit rounding gives 0.25+0.16+0.07+0.20 = 0.68 -> balance 33.68.
AMOUNTS = ["12.25", "7.75", "3.25", "9.75"]
EXPECTED_BALANCE = Decimal("33.66")
EXPECTED_BONUS = Decimal("0.66")
ACCOUNT = "probe-acct"


def run_cli(repo, args, db):
    return subprocess.run(
        [sys.executable, "cli.py"] + args + ["--db", db],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
    )


def main():
    if len(sys.argv) != 2:
        print("ERROR: usage: python3 probe_defect.py <repo-dir>")
        return 2
    repo = os.path.abspath(sys.argv[1])
    if not os.path.exists(os.path.join(repo, "cli.py")):
        print("ERROR: cli.py not found in repo")
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "ledger.json")
        try:
            for amount in AMOUNTS:
                r = run_cli(
                    repo,
                    ["apply", "--account", ACCOUNT, "--amount", amount],
                    db,
                )
                if r.returncode != 0:
                    print(
                        "ERROR: apply exited %d: %s"
                        % (r.returncode, (r.stderr or r.stdout).strip()[:200])
                    )
                    return 2
            r = run_cli(repo, ["balance", "--account", ACCOUNT], db)
        except subprocess.TimeoutExpired:
            print("ERROR: CLI timed out")
            return 2
        if r.returncode != 0:
            print(
                "ERROR: balance exited %d: %s"
                % (r.returncode, (r.stderr or r.stdout).strip()[:200])
            )
            return 2
        try:
            balance = Decimal(r.stdout.strip())
        except InvalidOperation:
            print("ERROR: unparseable balance output: %r" % r.stdout.strip()[:200])
            return 2

        # Secondary: bonus line on the statement, if present in the format.
        bonus = None
        try:
            s = run_cli(repo, ["statement", "--account", ACCOUNT], db)
        except subprocess.TimeoutExpired:
            print("ERROR: CLI timed out")
            return 2
        if s.returncode == 0:
            for line in s.stdout.splitlines():
                parts = line.split()
                if parts and parts[0].lower() == "bonus":
                    try:
                        bonus = Decimal(parts[-1])
                    except InvalidOperation:
                        pass

        if balance != EXPECTED_BALANCE:
            print(
                "FAIL: balance after credits %s is %s; spec (round once on the "
                "credit total) gives %s" % (AMOUNTS, balance, EXPECTED_BALANCE)
            )
            return 1
        if bonus is not None and bonus != EXPECTED_BONUS:
            print(
                "FAIL: statement bonus is %s; spec gives %s" % (bonus, EXPECTED_BONUS)
            )
            return 1
        print(
            "PASS: balance %s (and statement bonus) match the round-once spec"
            % balance
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
