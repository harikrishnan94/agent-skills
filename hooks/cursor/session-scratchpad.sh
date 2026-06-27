#!/usr/bin/env bash
# ~/.cursor/hooks/session-scratchpad.sh
#
# Cursor sessionStart hook (registered in ~/.cursor/hooks.json). Maintains a
# per-project, per-session scratchpad under ~/.cursor-session-scratchpads/.
#
# Cursor's sessionStart stdin differs from the others: there is NO `cwd` — the
# project root comes from the `workspace_roots` array — and context is injected
# via a TOP-LEVEL {"additional_context": "..."} object (snake_case).
#
# NOTE: as of the current Cursor docs the Cursor *CLI* (cursor-agent) only fires
# beforeShellExecution/afterShellExecution; sessionStart fires in the Cursor IDE.
# This hook is therefore effectively IDE-only until the CLI gains sessionStart.
set -euo pipefail

input=$(cat)
session_id=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("session_id") or d.get("conversation_id") or "session")')
cwd=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); r=d.get("workspace_roots") or []; print(r[0] if r else ".")')

[[ "$cwd" == /* ]] || exit 0

slug=$(printf '%s' "$cwd" | sed 's|^/||; s|/|-|g')
dir="$HOME/.cursor-session-scratchpads/$slug"
file="$dir/$session_id.md"
mkdir -p "$dir"

if [[ ! -f "$file" ]]; then
  printf '# Session scratchpad\nProject: %s\nSession: %s\nCreated: %s\n\n## Goal\n\n## Plan\n\n## Done\n\n## Current step\n\n## Open questions\n' \
    "$cwd" "$session_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$file"
fi

python3 - "$file" <<'PY'
import json, sys
path = sys.argv[1]
content = open(path).read()
ctx = (
    "SESSION SCRATCHPAD — durable working memory for this session.\n"
    f"Path: {path}\n"
    "Rules: update this file immediately after every completed step, decision, "
    "or plan change. After any compaction or resume, re-read it before doing "
    "anything else. It is the source of truth for task state, not the "
    "conversation history.\n\n"
    f"--- current contents ---\n{content}"
)
print(json.dumps({"additional_context": ctx}))
PY
