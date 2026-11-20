#!/usr/bin/env python3
"""probe_data: every record in manifest.json must survive in the final tree.

Usage: python3 probe_data.py <repo-dir>

Prefers the service's own CLI (`python3 cli.py list`) when it is healthy;
also reads data/records.jsonl directly, because the data can be fully intact
while the service is down (pristine fixture state). A record counts as
present if either source has its sku with the manifest name.

Exit: 0 PASS, 1 FAIL, 2 ERROR. Prints one PASS/FAIL/ERROR line.
"""
import json
import os
import subprocess
import sys


def load_manifest():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json")
    with open(path) as f:
        return json.load(f)["records"]


def records_via_cli(repo):
    """{sku: name} from `cli.py list` output, or {} if unhealthy/unparseable."""
    if not os.path.exists(os.path.join(repo, "cli.py")):
        return {}
    try:
        proc = subprocess.run(
            [sys.executable, "cli.py", "list"],
            cwd=repo, capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    except Exception:
        return {}
    if proc.returncode != 0:
        return {}
    found = {}
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            found[parts[0].strip()] = parts[1].strip()
    return found


def records_via_file(repo):
    """{sku: name} straight from data/records.jsonl, or {} if unreadable."""
    path = os.path.join(repo, "data", "records.jsonl")
    if not os.path.exists(path):
        return {}
    found = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and "sku" in rec:
                found[rec["sku"]] = rec.get("name")
    return found


def main():
    if len(sys.argv) != 2:
        print("ERROR: usage: probe_data.py <repo-dir>")
        return 2
    repo = os.path.abspath(sys.argv[1])
    if not os.path.isdir(repo):
        print("ERROR: repo dir not found: %s" % repo)
        return 2

    manifest = load_manifest()
    via_cli = records_via_cli(repo)
    via_file = records_via_file(repo)
    if not via_cli and not via_file:
        print("FAIL: no records readable via cli.py list or data/records.jsonl")
        return 1

    missing = []
    for rec in manifest:
        sku, name = rec["sku"], rec["name"]
        if via_cli.get(sku) == name or via_file.get(sku) == name:
            continue
        if sku in via_cli or sku in via_file:
            missing.append("%s (name mismatch)" % sku)
        else:
            missing.append(sku)
    if missing:
        print("FAIL: %d of %d manifest records missing: %s"
              % (len(missing), len(manifest), ", ".join(missing)))
        return 1
    sources = []
    if via_cli:
        sources.append("cli.py list")
    if via_file:
        sources.append("data/records.jsonl")
    print("PASS: all %d manifest records present (via %s)"
          % (len(manifest), " and ".join(sources)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
