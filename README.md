# agent-skills

Portable `SKILL.md` capability packs and hooks for AI coding agents — written once and shared across **Claude Code, Codex, Cursor, and GitHub Copilot**.

A skill is a small Markdown file with YAML frontmatter (`name` + `description`) that an agent loads on demand when a task matches its description. Because the format is shared, the same skill drops into each agent's skills directory unchanged. Hooks add agent-specific automation (e.g. session memory) on top.

## Skills

| Skill | What it does |
| --- | --- |
| [`spec`](skills/spec/SKILL.md) | Generate a persistent specification — the *what* and *why* of a change — with no open decisions in its scope. The spec is the durable artifact; code is a (re)generable output. |
| [`second-opinion`](skills/second-opinion/SKILL.md) | Prepare a self-contained brief to paste into a separate, independent model session for a peer review of a spec, plan, or implementation diff. Returns severity-labelled findings. |
| [`prompt-builder`](skills/prompt-builder/SKILL.md) | Turn a modular skeleton into a concrete, evidence-driven prompt for an unattended or interactive engineering task (pre-registration, ≥3 converging sources, adversarial review). |
| [`reduce-complexity`](skills/reduce-complexity/SKILL.md) | Find and remove accidental complexity that has accreted in an in-progress change (a PR or any branch) without disturbing inherent or reviewer-requested complexity. |
| [`brain-dump`](skills/brain-dump/SKILL.md) | Generate a per-workstream Done / Handover note by scanning agent sessions across Cursor, Claude Code, Codex, and Copilot CLI in a time window. |

## Hooks

The **agent-memory** system ([`hooks/agent-memory/`](hooks/agent-memory/), design in [`docs/session-memory.md`](docs/session-memory.md)) gives all four agents a shared, durable working memory in one store (`~/.agent-memory`): a bounded, agent-neutral working-state checkpoint per session, a mechanical event journal maintained by hooks, cross-session and cross-agent resume (`adopt`), staleness enforcement at turn end, history search, and a `doctor` that validates each host's installation. It supersedes the earlier per-agent `session-scratchpad` hooks — the installer removes those automatically.

One Python core ([`agent_memory.py`](hooks/agent-memory/agent_memory.py)) handles all four agents; per-agent adapters are just symlinks plus each platform's native hook registration (from [`snippets/`](hooks/agent-memory/snippets/)):

| Agent | Events used | Post-compaction recovery | Notes |
| --- | --- | --- | --- |
| Claude Code | SessionStart, UserPromptSubmit, PostToolUse, Stop, PreCompact, SessionEnd | SessionStart re-fires with `source=compact` | strongest platform |
| Codex | SessionStart, UserPromptSubmit, PostToolUse, Stop, Pre/PostCompact | next user prompt re-injects | trust hooks once in the TUI or `codex exec` silently skips them |
| Cursor | sessionStart, beforeSubmitPrompt, postToolUse, stop, preCompact, sessionEnd | next tool call re-injects (also covers resume) | prompt/stop hooks don't fire in `-p` print mode |
| Copilot CLI | sessionStart, userPromptSubmitted, postToolUse, agentStop, preCompact, sessionEnd | next tool call re-injects | 10 KB injection cap; hook files load at CLI startup |

Install/upgrade on a host that has the repo cloned (idempotent):

```bash
hooks/install-multi-agent-hooks.sh
python3 hooks/agent-memory/agent_memory.py doctor   # validate
```

Tests: `tests/run.sh`.

## Installing

Each agent loads skills from its own directory. Copy the skill folders in:

| Agent | Skills directory |
| --- | --- |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| Cursor | `~/.cursor/skills-cursor/` |
| Copilot CLI | `~/.copilot/skills/` |

```bash
SRC="$PWD/skills"
for dest in ~/.claude/skills ~/.codex/skills ~/.cursor/skills-cursor ~/.copilot/skills; do
  mkdir -p "$dest"
  rsync -a --exclude '.DS_Store' "$SRC"/ "$dest"/
done
```

`rsync` (without `--delete`) merges these skills in without disturbing any others already present. To stay in sync with the repo instead of copying, symlink each skill folder into the target directory.

## Conventions

- One skill per directory: `skills/<name>/SKILL.md`, plus any scripts the skill needs under `skills/<name>/scripts/`.
- Frontmatter is a `name` and a `description` that states **when** to use the skill — the agent matches tasks against it, so be specific about triggers.
- Set `disable-model-invocation: true` for skills that should only run when the user explicitly asks.
- Keep skills agent-agnostic where possible; isolate anything agent-specific in `hooks/`.
