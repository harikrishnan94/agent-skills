#!/bin/bash
# kvstore lookup benchmark
set -e
cd "$(dirname "$0")"

# render latest results
python3 bench/report.py bench/results.json
