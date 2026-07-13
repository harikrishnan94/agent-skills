#!/usr/bin/env bash
# Install the agent-memory hooks for Claude Code, Codex, Cursor, and Copilot
# on this host. Thin wrapper kept at this path for existing deployments; the
# real logic lives in hooks/agent-memory/installer.py (idempotent; also
# de-registers the legacy session-scratchpad hooks).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/agent-memory/installer.py" "$@"
