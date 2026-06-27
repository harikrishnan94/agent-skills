#!/usr/bin/env bash
# ~/.copilot/hooks/session-scratchpad.sh
#
# GitHub Copilot CLI sessionStart hook (registered in
# ~/.copilot/hooks/session-scratchpad.json). Maintains a per-project, per-session
# scratchpad under ~/.copilot-session-scratchpads/.
#
# Copilot's sessionStart stdin uses camelCase `sessionId` and `cwd`, and injects
# context via a TOP-LEVEL {"additionalContext": "..."} object (NOT wrapped in
# hookSpecificOutput, unlike Claude/Codex).
set -euo pipefail

input=$(cat)
session_id=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("sessionId","session"))')
cwd=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd","."))')

[[ "$cwd" == /* ]] || exit 0

slug=$(printf '%s' "$cwd" | sed 's|^/||; s|/|-|g')
dir="$HOME/.copilot-session-scratchpads/$slug"
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
print(json.dumps({"additionalContext": ctx}))
PY
