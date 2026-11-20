#!/bin/bash
# Build the echochamber fixture repo at $1: kvstore core, cache layer,
# benchmark docs, then the settings.json capacity step. Deterministic:
# fixed commit dates, seeded data generation.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$1"

mkdir -p "$DEST"
cd "$DEST"
git init -q -b main
git config user.name "Dev"
git config user.email "dev@example.com"
git config commit.gpgsign false  # a signing setup on the host must not leak into the fixture
git config tag.gpgsign false

commit() {
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git commit -qm "$2"
}

# -- commit 1: store core + dataset ------------------------------------------
cp -R "$SRC/base/kvstore" .
cp "$SRC/base/.gitignore" .
mkdir -p data
python3 - data/records.jsonl <<'EOF'
import json, random, sys
random.seed(20251103)
regions = ["us-east", "us-west", "eu-central", "ap-south"]
tiers = ["free", "pro", "enterprise"]
with open(sys.argv[1], "w") as fh:
    for i in range(4000):
        rec = {
            "key": "user-%06d" % i,
            "value": {
                "name": "user%d" % i,
                "region": random.choice(regions),
                "tier": random.choice(tiers),
                "score": round(random.uniform(0, 100), 2),
            },
        }
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
EOF
git add .gitignore kvstore/__init__.py kvstore/store.py data/records.jsonl
commit "2025-11-03T10:12:00 +0100" "add key-value store core and records dataset"

# -- commit 2: cache layer + CLI + tests --------------------------------------
cp "$SRC/base/kvstore/cache.py" kvstore/
cp "$SRC/base/cli.py" .
cp "$SRC/base/README.md" .
cp -R "$SRC/base/tests" .
git add kvstore/cache.py cli.py README.md tests
commit "2025-11-10T15:41:00 +0100" "add read-through LRU cache, CLI, and tests"

# -- commit 3: benchmark + docs ------------------------------------------------
cp "$SRC/bench_docs/bench.sh" .
chmod +x bench.sh
mkdir -p bench docs
cp "$SRC/bench_docs/bench/results.json" "$SRC/bench_docs/bench/report.py" "$SRC/bench_docs/bench/RESULTS.md" bench/
cp "$SRC/bench_docs/docs/perf-notes.md" docs/
cp "$SRC/bench_docs/README.md" .
git add bench.sh bench docs README.md
commit "2025-11-18T18:05:00 +0100" "benchmark the cache layer and write up results"

# -- commit 4: capacity moves into settings.json --------------------------------
cp "$SRC/config_step/kvstore/config.py" kvstore/
cp "$SRC/config_step/settings.json" .
cp "$SRC/config_step/cli.py" .
git add kvstore/config.py settings.json cli.py
commit "2025-12-02T11:27:00 +0100" "make cache capacity configurable via settings.json"
