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

The **session-scratchpad** hook maintains a per-project, per-session scratchpad as durable working memory that survives compaction and resume. It is ported to each agent's hook contract — each agent passes a different session-start payload and expects a different context-injection shape:

| Hook | Agent | Event | Injects via | Wire-up |
| --- | --- | --- | --- | --- |
| [`claude/session-scratchpad.sh`](hooks/claude/session-scratchpad.sh) | Claude Code | `SessionStart` / `PreCompact` | `hookSpecificOutput.additionalContext` | [`settings.snippet.json`](hooks/claude/settings.snippet.json) → `~/.claude/settings.json`; [`CLAUDE.snippet.md`](hooks/claude/CLAUDE.snippet.md) → `~/.claude/CLAUDE.md` |
| [`codex/session-scratchpad.sh`](hooks/codex/session-scratchpad.sh) | Codex | `SessionStart` | `hookSpecificOutput.additionalContext` | [`config.snippet.toml`](hooks/codex/config.snippet.toml) → `~/.codex/config.toml`; [`AGENTS.snippet.md`](hooks/codex/AGENTS.snippet.md) → `~/.codex/AGENTS.md` |
| [`copilot/session-scratchpad.sh`](hooks/copilot/session-scratchpad.sh) | Copilot CLI | `sessionStart` | top-level `additionalContext` | [`hooks.snippet.json`](hooks/copilot/hooks.snippet.json) → `~/.copilot/hooks/`; [`copilot-instructions.snippet.md`](hooks/copilot/copilot-instructions.snippet.md) → `~/.copilot/copilot-instructions.md` |
| [`cursor/session-scratchpad.sh`](hooks/cursor/session-scratchpad.sh) | Cursor | `sessionStart` | top-level `additional_context` (snake_case); reads `workspace_roots`, not `cwd` | [`hooks.snippet.json`](hooks/cursor/hooks.snippet.json) → `~/.cursor/hooks.json` |

> **Cursor caveat:** the Cursor CLI (`cursor-agent`) currently fires only `beforeShellExecution`/`afterShellExecution`; `sessionStart` fires in the Cursor **IDE**. The Cursor hook is therefore effectively IDE-only until the CLI gains `sessionStart`.

Each agent uses its own scratchpad store (`~/.<agent>-session-scratchpads/`). To install the Codex/Copilot/Cursor hooks on a host that has the repo cloned, run [`hooks/install-multi-agent-hooks.sh`](hooks/install-multi-agent-hooks.sh) (symlinks each script, registers it, appends the ingest instruction — idempotent).

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
