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

| Hook | Agent | What it does |
| --- | --- | --- |
| [`claude/session-scratchpad.sh`](hooks/claude/session-scratchpad.sh) | Claude Code | A `SessionStart` / `PreCompact` hook that maintains a per-project, per-session scratchpad as durable working memory that survives compaction and resume. |

Wire-up lives alongside the script: merge [`hooks/claude/settings.snippet.json`](hooks/claude/settings.snippet.json) into `~/.claude/settings.json` (hook registration + scratchpad permissions) and [`hooks/claude/CLAUDE.snippet.md`](hooks/claude/CLAUDE.snippet.md) into your global `~/.claude/CLAUDE.md` (the durable ingest instruction).

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
