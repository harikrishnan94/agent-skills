#!/usr/bin/env bash
# ~/.claude/hooks/session-scratchpad.sh
#
# User-level SessionStart hook (registered in ~/.claude/settings.json,
# matcher: startup|resume|compact). Maintains a per-project, per-session
# scratchpad under ~/.claude-session-scratchpads/ — outside the repo
# (zero git footprint) and outside harness-managed ~/.claude state.
# Requires the Read/Edit/Write allow rules for this path in settings.json.
set -euo pipefail

# --- read hook input from stdin ---
input=$(cat)

session_id=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin)["session_id"])')
cwd=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd","."))')

# --- skip when there is no real working directory ---
# Cursor also invokes this hook but passes `workspace_roots` instead of `cwd`,
# so `cwd` degrades to ".". In that case the Cursor-native hook
# (~/.cursor/hooks/session-scratchpad.sh) already handles the session; running
# here too would create a duplicate junk (cwd=".") scratchpad under the store
# root and inject a second, conflicting path. Real Claude Code CLI sessions
# always pass an absolute `cwd`, so this only short-circuits the Cursor case.
if [[ "$cwd" != /* ]]; then
  exit 0
fi

# --- derive per-project namespace from cwd (worktree-safe) ---
slug=$(printf '%s' "$cwd" | sed 's|^/||; s|/|-|g')
dir="$HOME/.claude-session-scratchpads/$slug"
file="$dir/$session_id.md"
mkdir -p "$dir"

# --- create scratchpad on first start; resumes/compactions reuse it ---
if [[ ! -f "$file" ]]; then
  printf '# Session scratchpad\nProject: %s\nSession: %s\nCreated: %s\n\n## Goal\n\n## Plan\n\n## Done\n\n## Current step\n\n## Open questions\n' \
    "$cwd" "$session_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$file"
fi

# --- inject path + current contents into session context ---
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