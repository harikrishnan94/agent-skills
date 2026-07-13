#!/usr/bin/env bash
# Run the agent-skills test suite (agent-memory core + installer).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec python3 -m unittest discover -s tests -v "$@"
