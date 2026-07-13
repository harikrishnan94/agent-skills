<!-- Durable ingest half of agent-memory. hooks/agent-memory/install.sh appends
     this section to each agent's global instruction file (Claude:
     ~/.claude/CLAUDE.md, Codex: ~/.codex/AGENTS.md, Copilot:
     ~/.copilot/copilot-instructions.md), replacing __HOOK__ with that agent's
     adapter path. Instruction files are reassembled every turn, so this text —
     unlike hook-injected context — survives compaction on every platform.
     Cursor has no reliable global instruction file; it relies on the
     mechanical postToolUse re-injection instead. -->

## Agent working memory
A cross-agent working-state file is maintained for every session by the
agent-memory hooks (store: `~/.agent-memory`; your file's exact path is
injected at session start).
- The state file is the source of truth for task state — over conversation
  history and over any agent-native memory.
- Update it immediately after every completed step, decision, plan change, or
  failed hypothesis. Rewrite sections in place — never append a log. Keep it
  under ~120 lines; set `Status: done` when the objective is complete.
- After any compaction, resume, or gap: re-read the file before doing anything
  else.
- Unfinished work from earlier sessions (any agent, any worktree) is offered at
  session start — if the request continues that work, run the provided adopt
  command first instead of reconstructing state from memory.
- To recall prior work in this project: `python3 __HOOK__ search "<regex>"`
  (`--all-projects` widens it); `python3 __HOOK__ status` lists sessions and
  their states.
