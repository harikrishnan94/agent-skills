#!/usr/bin/env bash
# Install the session-scratchpad hook for Codex, Copilot, and Cursor on this host.
# Symlinks each agent's hook script from the agent-skills clone, registers it in the
# agent's config, and appends the durable ingest instruction. Idempotent.
#
# Assumes the repo is cloned at ~/projects/agent-skills (see install script for skills).
set -euo pipefail

REPO="$HOME/projects/agent-skills"
[ -d "$REPO/hooks" ] || { echo "!! $REPO not found — clone the repo first"; exit 1; }

# Extract just the "## Session state tracking" section from a snippet file.
ingest() { awk '/^## Session state tracking/{p=1} p' "$1"; }

############################## Codex ##############################
mkdir -p "$HOME/.codex/hooks"
ln -sfn "$REPO/hooks/codex/session-scratchpad.sh" "$HOME/.codex/hooks/session-scratchpad.sh"
echo "[codex] linked hook script"

if grep -q "session-scratchpad" "$HOME/.codex/config.toml" 2>/dev/null; then
  echo "[codex] config.toml already references the hook — left untouched"
else
  cp -n "$HOME/.codex/config.toml" "$HOME/.codex/config.toml.bak" 2>/dev/null || true
  cat >> "$HOME/.codex/config.toml" <<EOF

# session-scratchpad hook (added by agent-skills)
[[hooks.SessionStart]]
matcher = "startup|resume|compact"

[[hooks.SessionStart.hooks]]
type = "command"
command = "bash $HOME/.codex/hooks/session-scratchpad.sh"
statusMessage = "Loading session scratchpad"
EOF
  echo "[codex] appended SessionStart hook to config.toml (backup: config.toml.bak)"
fi

if grep -q "Session state tracking" "$HOME/.codex/AGENTS.md" 2>/dev/null; then
  echo "[codex] AGENTS.md already has the section — left untouched"
else
  printf '\n' >> "$HOME/.codex/AGENTS.md"
  ingest "$REPO/hooks/codex/AGENTS.snippet.md" >> "$HOME/.codex/AGENTS.md"
  echo "[codex] appended Session state tracking to AGENTS.md"
fi

############################## Copilot ##############################
mkdir -p "$HOME/.copilot/hooks"
ln -sfn "$REPO/hooks/copilot/session-scratchpad.sh" "$HOME/.copilot/hooks/session-scratchpad.sh"
cat > "$HOME/.copilot/hooks/session-scratchpad.json" <<EOF
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      { "type": "command", "bash": "bash $HOME/.copilot/hooks/session-scratchpad.sh", "timeoutSec": 30 }
    ]
  }
}
EOF
echo "[copilot] linked hook script + wrote ~/.copilot/hooks/session-scratchpad.json"

if grep -q "Session state tracking" "$HOME/.copilot/copilot-instructions.md" 2>/dev/null; then
  echo "[copilot] copilot-instructions.md already has the section — left untouched"
else
  [ -f "$HOME/.copilot/copilot-instructions.md" ] && printf '\n' >> "$HOME/.copilot/copilot-instructions.md"
  ingest "$REPO/hooks/copilot/copilot-instructions.snippet.md" >> "$HOME/.copilot/copilot-instructions.md"
  echo "[copilot] appended Session state tracking to copilot-instructions.md"
fi
command -v copilot >/dev/null 2>&1 || echo "[copilot] NOTE: copilot CLI not installed here — hook is staged but dormant"

############################## Cursor ##############################
mkdir -p "$HOME/.cursor/hooks"
ln -sfn "$REPO/hooks/cursor/session-scratchpad.sh" "$HOME/.cursor/hooks/session-scratchpad.sh"
[ -f "$HOME/.cursor/hooks.json" ] && cp -n "$HOME/.cursor/hooks.json" "$HOME/.cursor/hooks.json.bak" 2>/dev/null || true
python3 - "$HOME/.cursor/hooks.json" "$HOME/.cursor/hooks/session-scratchpad.sh" <<'PY'
import json, sys, os
path, cmd = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        cfg = json.load(f)
except FileNotFoundError:
    cfg = {}
cfg.setdefault("version", 1)
ss = cfg.setdefault("hooks", {}).setdefault("sessionStart", [])
if not any(isinstance(e, dict) and e.get("command") == cmd for e in ss):
    ss.append({"command": cmd})
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
print("[cursor] merged sessionStart into ~/.cursor/hooks.json")
PY
command -v cursor-agent >/dev/null 2>&1 || echo "[cursor] NOTE: cursor-agent not installed here — hook is staged but dormant"
echo "[cursor] NOTE: Cursor CLI fires only before/afterShellExecution; sessionStart works in the Cursor IDE"

echo "[done] multi-agent hooks on $(hostname)"
