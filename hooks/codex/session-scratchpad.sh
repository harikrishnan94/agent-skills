#!/usr/bin/env bash
# ~/.codex/hooks/session-scratchpad.sh
#
# Codex SessionStart hook (registered in ~/.codex/config.toml under
# [[hooks.SessionStart]], matcher: startup|resume|compact). Maintains a
# per-project, per-session scratchpad under ~/.codex-session-scratchpads/ —
# outside any repo and outside ~/.codex state.
#
# Codex SessionStart passes `session_id` and `cwd` on stdin, and injects context
# via hookSpecificOutput.additionalContext — the same contract as Claude Code, so
# this script is structurally identical to hooks/claude/session-scratchpad.sh; only
# the store directory differs.
set -euo pipefail

input=$(cat)
session_id=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id","session"))')
cwd=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd","."))')

# Need a real absolute working dir; otherwise no-op (avoid junk scratchpads).
[[ "$cwd" == /* ]] || exit 0

slug=$(printf '%s' "$cwd" | sed 's|^/||; s|/|-|g')
dir="$HOME/.codex-session-scratchpads/$slug"
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
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))
PY
