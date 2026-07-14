# agent-memory: cross-agent session memory

`agent-memory` gives Claude Code, Codex, Cursor, and Copilot CLI a shared,
durable working memory that survives context compaction, interruption, resume,
session replacement, and movement between agent products, worktrees, and
machines (where the store is synced). It replaces the earlier per-agent
`session-scratchpad` hooks.

Everything lives in `hooks/agent-memory/`:

| File | Role |
| --- | --- |
| `agent_memory.py` | single-file core: hook handlers, adapters, CLI (`status`, `search`, `adopt`, `doctor`, …) |
| `installer.py` | idempotent installer/upgrader for all four agents (also de-registers the legacy scratchpad hooks) |
| `snippets/` | the exact config and instruction fragments the installer applies (also usable manually) |
| `VERSION` | version stamp checked by `doctor` |

Install on a host that has this repo cloned:

```bash
hooks/install-multi-agent-hooks.sh     # wraps hooks/agent-memory/installer.py
python3 hooks/agent-memory/agent_memory.py doctor   # validate any time
```

## Conceptual model

Three kinds of information, with different lifecycles:

1. **Working state** (`state.md`, per session) — the *authoritative checkpoint*:
   Objective, Constraints & decisions, Done (verified), Failed hypotheses,
   Now (exact stopping point), Next, Open questions, plus a `Status:` line
   (`in-progress` / `done` / `abandoned`). Written and rewritten **by the
   model** using its normal file tools. Bounded (~120 lines guidance;
   injection truncates at ~8 KB). Agent-neutral: no tool names, transcript
   schemas, or hook terminology from any one product.
2. **Journal** (`journal.jsonl`, per session) — *mechanical* event capture by
   the hooks, independent of model compliance: session starts (with source),
   prompts (truncated), state-changing tool calls, compactions, stops
   (with staleness verdict), session end (with reason), adoptions, gaps.
   Append-only, rotated once at 2 MB (the rotated generation stays visible to
   staleness checks and `search`).
3. **Native transcripts** — each agent's own full history stores
   (`~/.claude/projects`, `~/.codex/sessions`, `~/.cursor/projects/...`,
   `~/.copilot/session-state`). agent-memory records `transcript_path` in
   session metadata where the agent provides it, but does not copy
   transcripts. They remain the raw historical evidence; the `brain-dump`
   skill knows how to parse all four formats.

The split answers the growth problem: the checkpoint stays small and current
(stale plans are rewritten away, not appended), the journal keeps a bounded
mechanical record, and full history stays in the native stores where it
already exists.

### One authority

The state file is defined — in the injected rules and in each agent's global
instruction file — as authoritative for *execution state*, over conversation
history and over agent-native memory. Agent-native stores keep what they are
good at: preferences, project instructions, durable docs, raw history.
The installer removes the legacy scratchpad hooks so no second memory
authority runs alongside.

## Store layout

```
~/.agent-memory/                      (override: AGENT_MEMORY_HOME)
  store.json                          schema version
  log/hooks.log                       hook errors (hooks never fail the agent)
  sessions-index/<agent>-<sid>        session -> project (fast path, no git)
  projects/<name>-<hash10>/
    project.json                      identity kind/key, worktrees seen, remote
    sessions/<agent>-<session-id>/
      meta.json                       provenance, heartbeat, status, counters
      state.md                        the checkpoint (model-owned)
      journal.jsonl                   mechanical events (hook-owned)
      archive/state-*.md              states superseded via `fresh`
    archive/<agent>-<session-id>/     sessions moved by `prune` (still searched)
```

## Project identity

Directory key = `<sanitized-basename>-<sha256(kind:key)[:10]>`. Lookup is by
hash suffix, so the human prefix is cosmetic. Identity precedence:

1. **`git-root-commit`** — the repo's root commit SHA. Identical across
   clones, forks of the same history, and every worktree, on every machine.
2. **`git-remote`** — normalized `host/owner/repo`, used when the clone is
   **shallow** (a shallow clone's root commit is the truncation point, which
   would split identity).
3. **`path`** — `realpath` of the toplevel/cwd for non-git directories
   (symlink-safe, but inherently machine-local).

Consequences, stated explicitly:

- Separate **worktrees** and separate **clones** of one repo are the *same
  project*; each session records which worktree it ran in, and candidates
  from another worktree are labeled as such.
- A **history rewrite** that changes the root commit changes the identity
  (old sessions stay under the old project dir; `search --all-projects`
  still reaches them).
- **Non-git** directories don't match across machines.
- The old lossy `/`→`-` slugs (where `a/b-c` == `a/b/c`) are gone.

## Lifecycle: what each hook does

Six normalized events, dispatched as `agent_memory.py hook <agent> <event>`:

| Normalized | Purpose |
| --- | --- |
| `session-start` | create/adopt session record; inject state (own state on resume/compact, or resumable candidates on a fresh session) |
| `prompt` | journal the prompt; on Codex, perform pending re-injection |
| `post-tool` | journal state-changing tools; perform pending re-injection; else fire the mid-turn staleness **nudge** when due (never on subagent-fired events) |
| `stop` | staleness check — block once (loop-guarded) if work happened after the last checkpoint write |
| `pre-compact` / `post-compact` | journal; arm re-injection on agents whose session-start does not re-fire after compaction |
| `session-end` | record clean end + reason |

### Capability matrix (verified 2026-07)

| Capability | Claude Code | Codex | Cursor | Copilot CLI |
| --- | --- | --- | --- | --- |
| session-start fires on | startup, resume, `/clear`, **after compaction** | startup, resume (manual `/compact` does **not** re-fire) | new session only (**not** resume, **not** compaction) | startup, **resume** |
| observe prompt | yes + inject | yes + inject | yes (not in `-p` mode), no inject | yes, no inject |
| observe tools | yes + inject | yes + inject | yes + inject (only mid-session inject channel) | yes + inject |
| stop can force continue | yes (`decision:block`, `stop_hook_active` guard) | yes (JSON-only, same guard) | yes (`followup_message`, interactive only, `loop_limit`) | yes (`decision:block`) |
| session-end event | yes | **no** | yes (fires per CLI process exit) | yes |
| post-compaction recovery | SessionStart(`compact`) re-injects | next `prompt` re-injects | next `post-tool` re-injects | next `post-tool` re-injects |
| injection size limit | generous (10k chars/output) | **~2,500 tokens** (larger output is spilled to a file) | none documented | **10 KB** merged per event |
| voluntary mid-turn checkpointing (live-probed 2026-07-14, n=1 each) | **no** — stop-hook-forced | **yes** — per-step (5 writes in one turn) | no — stop-hook-forced | **no** — stop-hook-forced (0 writes across a 5-tool turn) |
| mid-turn nudge delivery | yes (docs-confirmed: lands next to the tool result) | source-confirmed sink; dormant in practice (self-checkpoints before threshold) | **emitted but dropped upstream** (staff-confirmed bug, ≤ v3.7.x) | **yes — live-verified on 1.0.70**; regression-prone channel (#2980) |
| special risk | Task-subagent tools fire hooks under the parent session id (payload carries `agent_id`/`agent_type` — injections are gated on it) | **trust gate**: untrusted hooks silently skipped in `codex exec` | `beforeSubmitPrompt`/`stop` don't fire in `-p` print mode | hook configs load at CLI startup only; denied tool calls fire no postToolUse |

### Per-agent guarantees and degraded modes

**Claude Code** — strongest. Recovery after compaction and resume is native
(SessionStart re-fires with `source`). Stop-hook staleness enforcement works
headless and interactive. Degraded: none known.

**Codex** — SessionStart covers startup/resume; manual `/compact` only fires
Pre/PostCompact (which cannot inject), so recovery lands on the **next user
prompt**. Between compaction and that prompt the model relies on
`~/.codex/AGENTS.md` (reassembled every turn — it survives compaction).
No SessionEnd: a session that stops cleanly is distinguishable from a crash
only by its journal (`stop` with fresh checkpoint) and heartbeat age.
**Operational requirement:** after install/upgrade, open `codex`
interactively once and trust the hooks; until then `codex exec` silently
skips them (`doctor` warns about this).

**Cursor** — sessionStart does not re-fire on resume or compaction; both are
covered mechanically by the **gap detector** (a journaled event after a
45-minute silence or after a recorded sessionEnd arms re-injection) and the
**compaction detector** (preCompact arms re-injection); the next tool call
restores state. **Known upstream bug (staff-confirmed, ≤ v3.7.x): the
`postToolUse` `additional_context` we emit is accepted by the hook runner but
never delivered to the model** — so re-injection and nudges are inert on
Cursor until that ships; the working deliveries are the new-session start
(including candidates + breadcrumbs) and the `followup_message` stop channel.
In `cursor-agent -p` print mode, prompt and stop hooks do not fire —
staleness enforcement is degraded to the next-session warning. Cursor has no
reliable global instruction file, so the injected rules are the only standing
instructions. Cursor passes `workspace_roots`, not `cwd`.

**Copilot CLI** — sessionStart fires on resume (source `resume`), preCompact
cannot inject and has no postCompact, so post-compaction recovery lands on
the next tool call. postToolUse injection is live-verified end-to-end on
1.0.70 (the text appears in model request payloads), and agentStop honors the
Claude-shaped `{"decision":"block","reason"}` with auto-resume — but the
channel has a regression history (copilot-cli #2980, #2652, #3727): re-smoke
after CLI upgrades. Injection capped at 10 KB (our budget stays under 8 KB).
`userPromptSubmitted` is observe-only. Hook files are read at CLI startup
only (the installer prints a restart reminder when the wiring changes; the
adapter script itself updates in place). Denied tool calls fire no
postToolUse, so an all-denied turn is invisible to the staleness counter.
The durable ingest lives in `~/.copilot/copilot-instructions.md`.

### What is captured, uniformly and not

- Uniform (all four): session start/end boundaries*, prompts*, state-changing
  tool calls, compaction markers*, stop verdicts*, nudge deliveries (with
  uncheckpointed count and escalation level), adoption lineage, worktree/cwd,
  timestamps. (*subject to the per-agent gaps above: Codex has no
  session-end; Cursor `-p` mode misses prompt/stop.)
- Agent-specific, recorded when offered: `transcript_path`, session `source`,
  end `reason`.
- Not captured by any supported interface: model reasoning, in-context
  tool results (only names/targets are journaled), IDE-side activity where
  hooks don't fire. Cross-agent portability is *not* claimed for these.

## Cross-session and cross-agent resume

A fresh session's start injection lists up to 3 **resumable candidates** for
the project: sessions (any agent, any worktree) whose state differs from the
template and whose `Status:` is not `done`/`abandoned`, newest first, each
labeled `active` / `interrupted` / `ended` (+ `stale-checkpoint` when the
journal shows work after the last state write). The most recent candidate's
state is inlined read-only when it is under ~4 KB; every candidate line
carries its state file's path for direct reading. Sessions whose state was
adopted by a newer session are superseded and not re-offered — the lineage
tip is.

To continue one, the model runs the provided command:

```bash
python3 <adapter> adopt codex-0198… --into claude-4e8d…
```

Adoption **copies** the source state into the new session's state file and
records `resumed_from` in the new session's meta; the source's `adopted_by`
view is derived from that at read time (`show`). The source session's files
are never touched, so:

- previous state stays attributable and recoverable;
- two sessions adopting the same source is visible, not corrupting;
- `adopt` refuses to overwrite a state you already wrote (`--force` to
  override) — protecting "intentionally new work" from accidental resume.

Distinguishing the cases in problem statement §1:

| Situation | Mechanism |
| --- | --- |
| resume same session | same session id → same session dir; state re-injected |
| resume abandoned work | candidate list → `adopt` |
| intentionally new work | ignore candidates; state starts from template |
| fork from existing | `adopt` (lineage recorded), then diverge |
| second concurrent session | `active` label + CAUTION warning; adopt requires user confirmation per injected rules |
| another worktree | same project; candidate labeled with its worktree |
| another machine | same project id if the store is synced (git identity is machine-independent) |

## Concurrency and crash safety

- **Single-writer discipline**: a session's hooks write only that session's
  files. Cross-session facts (adoption) are recorded in the *adopting*
  session and derived at read time — no shared mutable index to corrupt.
  (`sessions-index/` is a per-session pointer file, also single-writer.)
- All JSON/state writes are **atomic** (temp file + `os.replace`). Journal
  appends are single `write()` calls in append mode.
- Same-session hook invocations can overlap (verified on Codex: SessionStart
  and UserPromptSubmit fire simultaneously on the first prompt): meta updates
  are last-writer-wins between valid snapshots; counters are approximate by
  design.
- **Freshness/ownership**: `active` = last hook event under 15 minutes ago
  (`AGENT_MEMORY_ACTIVE_MIN`) and no session-end. There is no lock that
  *prevents* two sessions working — agents can't be forced to cooperate —
  but both sessions see the warning, and neither can destroy the other's
  checkpoint.
- **Abnormal termination**: crash/kill/API error leaves the last state.md
  (atomic) plus every journaled event after it. The next session sees the
  candidate labeled `interrupted` with `stale-checkpoint` when applicable —
  a failure never masquerades as a clean checkpoint. A hook that itself
  crashes logs to `~/.agent-memory/log/hooks.log` and exits 0 (never breaks
  the host agent).

## Staleness enforcement (two stages)

**Stage 1 — advisory mid-turn nudge (post-tool).** Live probes (2026-07-14)
showed only Codex checkpoints voluntarily mid-turn; Claude, Cursor, and
Copilot write state.md only when the stop hook forces it, so a mid-turn crash
loses the whole turn. The nudge closes that gap: when
≥ `AGENT_MEMORY_NUDGE_TOOLS` (5; template state: 2; `0` disables)
state-changing tool calls accumulated since the last state write, the
post-tool hook injects a one-line reminder to checkpoint now. Throttles, all
ours (no platform dedups repeated injections):

- **Recency guard** — no nudge within `AGENT_MEMORY_NUDGE_COOLDOWN_MIN` (5)
  minutes of the last nudge, the last state-carrying injection, or the last
  stop block. Session-start stamps `last_inject`, so the first window after
  any start/compact is a deliberate blackout (the state was just delivered).
- **Episode cap** — at most two reminders per staleness episode (the second
  escalates, worded to promise only what the stop hook will actually do,
  including under `ENFORCE=soft`); after that, silence — the stop block is
  stage 3 of the same episode. A state write closes the episode.
- **Subagent gate** — events fired by Claude Task subagents (detected via
  `agent_id`/`agent_type` in the payload) journal their work but never
  receive a nudge or consume a pending re-injection: injected text would land
  in the subagent's context and tell it to overwrite the parent's checkpoint.
- The nudge fires on all four agents' post-tool channels; it is inert on
  Cursor (upstream drops the context — self-activates when fixed) and
  near-dormant on Codex (voluntary cadence rarely crosses the threshold).

Each delivery is journaled (`{"ev": "nudge", "uncheckpointed": n, "count": c}`),
so compliance is measurable: a `nudge` followed by a state-mtime advance is a
model that acted. Cost: the staleness scan runs per mutating tool call outside
the cooldown window (journal ≤ 2 MB + one rotation; accepted over caching
complexity).

**Stage 2 — blocking stop.** At `stop`, the checkpoint is stale when
≥ `AGENT_MEMORY_STALE_TOOLS` (3) state-changing tool calls were journaled
after `state.md` was last written (≥ 1 if the state is still the untouched
template). If stale, the hook blocks the stop once with instructions to
update the file. Guards against loops: `stop_hook_active` (Claude/Codex
payload field), a 30-minute per-session rate limit, and Cursor's own
`loop_limit`. A stop the *user* caused is never blocked: Cursor reports
`status: aborted|error` and the hook stands down (Codex exposes no such
signal on its Stop event — a user interrupt there can trigger one enforcement
block; the rate limit bounds the annoyance). The model's own writes to the
state file are excluded from the work counter, and prompts never count — a
tool-free Q&A session is never declared stale. `AGENT_MEMORY_ENFORCE=soft`
downgrades blocking to journal-only (the nudge still fires — soft means
"don't interrupt", advisory context is welcome); the staleness verdict still
surfaces in the next session's injection either way.

Double-registered hooks (e.g. Codex honoring both `config.toml` and
`hooks.json`) would fire twice per tool and double every count: identical
back-to-back journal records within 0.5 s are collapsed at read time, so
thresholds and the `n` quoted in enforcement messages reflect real activity
(`doctor` still warns about the duplicate registration itself). The collapse
is deliberately narrow — never for records without a target (distinct
NotebookEdit/MCP calls would alias) — because eating real work would silently
disarm the stop block; a double-fired target-less tool counting twice is the
safer error.

## Stale-state breadcrumbs

Wherever a **stale** state file is injected, a short auto-generated digest of
the uncheckpointed tool journal tail (last 10 events + total) is appended
after the state body — raw evidence of what happened after the last
checkpoint, requiring zero model cooperation. Delivery points: resume/compact
re-injection, the session-start stale warning, and the fresh-session
candidates offer (the top candidate's tail — this is the one path every
agent receives on a working channel, and the only one Cursor gets). The
digest is appended before truncation, so an oversized state body trims the
breadcrumbs first, never the reverse.

## Querying history

```bash
python3 <adapter> status [--all-projects] [--json]   # sessions, states, staleness
python3 <adapter> search "<regex>" [--all-projects] [--limit N]
python3 <adapter> show <session-key>                 # state + meta + journal tail
```

`search` covers states, journals, and archived sessions with provenance
(project/session, file, line), newest first — answering "did we already try
X?" without loading transcripts. For deep transcript archaeology, use the
native stores (via `transcript_path` in `show`) or the `brain-dump` skill.
Retention: `prune --days N` moves ended sessions to the project archive
(still searched, no longer offered or scanned at session start).

## Context growth control

Injected context is budgeted, not replayed: session-start injects one state
(≤ ~8 KB after truncation) + candidate summaries; re-injection injects one
state; everything else is on-demand via `search`/`show`. The 8 KB default
(`AGENT_MEMORY_MAX_INJECT`) respects Copilot's 10 KB cap, but 8 KB of dense
text is ~2,400–2,700 tokens — straddling Codex's ~2,500-token spill — so
Codex injections are capped tighter (6 KB, `INJECT_BUDGETS`), and the
candidates branch applies a whole-message cap. Nudges add ≤ ~400 bytes at
most twice per staleness episode; breadcrumbs add ≤ ~1.5 KB and only when a
stale state is being delivered anyway.

## Installation, validation, drift

`installer.py` (via `hooks/install-multi-agent-hooks.sh`) is idempotent and
per-agent:

- symlinks the adapter (`~/.<agent>/hooks/agent-memory.py`) into the clone,
  so `git pull` updates every agent at once;
- merges registrations (JSON merge for Claude/Cursor, per-group `[[hooks.*]]`
  management for Codex TOML — Codex itself rewrites config.toml with trust
  entries and `codex mcp add` tables, so only groups whose command references
  agent-memory/session-scratchpad are ever touched, everything else survives
  byte-for-byte — and a dedicated file for Copilot), preserving unrelated
  config and backing up each file once (`*.bak`);
- writes zero-argument executable wrappers for Cursor (the IDE is not
  guaranteed to shell-process hook commands);
- replaces the legacy `## Session state tracking` instruction sections and
  de-registers/removes all `session-scratchpad` hooks and scripts (the old
  `~/.<agent>-session-scratchpads` stores are left untouched and reported by
  `doctor`).

`doctor` validates per host: store writable, schema not newer than the code,
adapter present and byte-identical to the running copy (drift), every event
registered, legacy hooks gone, instruction sections present, Codex trust
entries present (warns otherwise), duplicate Codex registration
(config.toml + hooks.json would run hooks twice), CLI presence (info).
Exit code: 0 ok/warn, 1 on failures. `--json` for machines.

## Portability

- Python 3.8+ stdlib only; bash pieces are bash-3.2 compatible (macOS).
- Paths derive from `$HOME`/`AGENT_MEMORY_HOME`; no Linux/macOS assumptions.
- Cursor wrappers avoid shell-expansion assumptions in hook commands.
- Known limitations: Windows is untested (POSIX `fcntl` locking degrades to
  no-op, `os.replace` semantics differ for open files); Cursor cloud agents
  and Copilot cloud agents run hooks from project/enterprise scope only —
  user-scope hooks (this system) do not fire there; a `$HOME` containing
  spaces gets a shell-quoted Cursor hook command (correct for the CLI, which
  shell-processes commands; IDE behavior for such paths is unverified);
  syncing `~/.agent-memory` across machines is delegated to the user's
  tooling (files are small, atomic, conflict-safe per session).

## Failure recovery cheat-sheet

| Symptom | Recovery |
| --- | --- |
| hooks seem silent | `doctor`; on Codex check the trust gate; on Copilot restart the CLI |
| mid-turn nudges too chatty / unwanted | `AGENT_MEMORY_NUDGE_TOOLS=0` disables them (stop-block enforcement unaffected); raise `AGENT_MEMORY_NUDGE_COOLDOWN_MIN` to space them out |
| state file wrong/corrupt | previous versions in `archive/` (after `fresh`), journal shows what happened since |
| two sessions fought over a task | both states exist under their own sessions; `status` + `show` both, adopt the survivor |
| store schema newer than code | `git pull` the clone (doctor fails closed) |
| emergency disable | `AGENT_MEMORY_DISABLE=1` (hooks no-op) |
