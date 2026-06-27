---
name: brain-dump
description: >-
  Generate a per-workstream Done and Handover note ("brain dump") by scanning
  all agent sessions in a time window across Cursor (local IDE chats AND cloud /
  background / worktree sessions), Claude Code, Codex, and Copilot CLI. Use when
  the user asks for a brain dump, daily notes, end-of-day summary, handover
  notes, a "what did I do" recap, or to capture done / handover items across
  projects. Default window is since the last invocation; also accepts a duration
  (2d, 8h) or a date.
disable-model-invocation: true
---

# Brain Dump: Done / Handover Notes

Scan every agent session in a time window — Cursor (IDE and cloud / worktree
sessions), Claude Code, Codex, and Copilot CLI — group the work by workstream (a
PR, a branch, a topic — NOT by workspace or by tool), and emit a single chat
note — written as **plain markdown, not wrapped in a code fence**, so the user
can copy it straight
into Notion — split into **Handover** (what's in-flight / needs picking up) and
**Done** (what shipped). Output goes to chat only — do not write files (except the
skill's own last-run state) and do not push to Notion.

The canonical home of this skill is the git repo `~/brain-dump`; the Cursor,
Claude Code, Codex, and Copilot skill directories are symlinks to it. Scripts
and the last-run state are shared, so marking a run from any tool advances the
single window for all of them.

## Scripts

Run with the absolute paths below (canonical home `~/brain-dump/`).

- `scripts/list_sessions.py [WINDOW]` — index sessions across all projects
  and all four chat stores. A session is listed when its activity overlaps the
  window. Sessions are time-ordered, so a `## cursor:` / `## claude:` /
  `## codex:` / `## copilot:` group header can repeat when the stores interleave.
  - `WINDOW` is optional: a duration (`30m`, `8h`, `2d`, `1w`), a date
    (`2026-06-08`), `today`, or `yesterday`. Omit it for **since last run**.
  - `--json` for machine-readable output, `--exclude-session UUID` to drop a
    session, `--exclude-current` to auto-drop the live Claude Code session the
    script runs under, `--source cursor|claude|codex|copilot|all` to restrict
    the store, `--include-empty` to keep sessions with zero real user turns, and
    `--mark-run` to record "now" as the last invocation and exit.
- `scripts/condense_session.py PATH [--max-chars N]` — compact, turn-by-turn
  summary of one transcript (user query + assistant prose + one-line tool
  calls). The transcript format (Cursor / Claude Code / Codex / Copilot CLI) is
  auto-detected; Claude Code subagent transcripts
  (`<session>/subagents/agent-*.jsonl`) work too. Tail is kept when capped,
  because the final summary matters most; the cap is soft — the final turn is
  kept whole even when it alone exceeds `--max-chars`.

## Workflow

Copy this checklist and track progress:

```
- [ ] 1. Resolve window and list sessions
- [ ] 2. Identify and exclude the current (brain-dump) session
- [ ] 3. Condense each session
- [ ] 4. Group findings into workstreams
- [ ] 5. Verify hard state (read-only)
- [ ] 6. Compose the note in chat
- [ ] 7. Mark the run
```

### 1. Resolve window and list sessions

Run `list_sessions.py` with the user's window argument, or no argument for
"since last invocation". Note the resolved window printed in the header — the
note's date heading comes from it.

```bash
python3 ~/brain-dump/scripts/list_sessions.py 2d --exclude-current
```

### 2. Identify and exclude the current session

One of the listed sessions IS this brain-dump conversation; exclude it so the
note doesn't summarize itself.

- Under **Claude Code**, `--exclude-current` handles this automatically (it
  matches the live session via process ancestry; stderr names the excluded
  uuid).
- Under **Cursor**, **Codex**, and **Copilot**, `--exclude-current` prints a
  notice and excludes nothing. Identify this conversation manually (typically
  the newest session in the current project whose first query is this request)
  and re-run:

```bash
python3 ~/brain-dump/scripts/list_sessions.py 2d --exclude-session <this-uuid>
```

If you cannot pin it down, proceed but never emit a "brain-dump" workstream.

### 3. Condense each session

Condense every remaining session. Default `--max-chars` is fine; raise it for
long, high-signal sessions. Read the condensed output — focus on each session's
**final assistant summary** and any user instructions, which carry the
shipped/decided state. The per-turn `[timestamp]` lets you ignore turns that
fall outside the window for sessions that started earlier — but note it is
the **user-message** time: a long turn started before the window may have
completed inside it, so judge by the work, not the stamp alone. For Claude Code
sessions with subagents, condense a subagent transcript only when the parent
session looks high-signal and references its result.

### 4. Group findings into workstreams

Merge across sessions, project folders, and tools by the **thing being worked
on**: a PR number (`PR #106538`), a branch (`phj4` / `RHJ`), or a topic. A
single workstream often spans several sessions, several project folders
(local repo + a cloud worktree + a bench rig), and both Cursor and Claude
Code. Render each workstream as a **bold single-line** label (e.g.
`**PR #106538 — …**`, `**RHJ**`), not a heading — exactly as in the example below.

### 5. Verify hard state (read-only)

Before asserting facts, confirm them with read-only checks — do not trust the
transcript alone:

- Branch / commit claims: `git -C <repo> log --oneline -5`, `git -C <repo> status -sb`
  (is it really committed? pushed? working tree clean?). For "pushed" / "on
  the PR" claims, check the actual remote head — `git -C <repo> ls-remote
  origin <branch>` or `gh pr view <n> --json headRefOid` — transcripts often
  claim pushes that never happened.
- "Machine left non-default" claims (leftover cgroups, pinned cores, running
  servers, mounts): check whether the state is **still present** now
  (e.g. `ls /sys/fs/cgroup/<name>`, `pgrep -a clickhouse`). Only flag with ⚠️
  if it persists, and include the teardown steps.

Never run anything that changes state during verification.

### 6. Compose the note in chat

Write the note as **plain markdown, directly in your reply** — do NOT wrap it in
a ` ``` ` code fence. A fenced block pastes literal ` ``` ` lines into Notion and
stops the markdown from converting into real headings and to-dos; emitting the raw
markdown lets Notion turn `##`/`###` into headings and `- [ ]` into to-do blocks on
paste. Keep any surrounding prose minimal so the note itself copies cleanly.

Follow this structure. It is tuned for Notion, which renders `##`/`###` as headings
and `####`+ as plain bold text — so never go past `###`, and never use `#` (that
level belongs to the Notion page title):

- **Date heading** `## <Month D, YYYY>`, or `## <Month D> – <Month D, YYYY>` if
  the window spans multiple days.
- **Two sections** `### Handover` then `### Done`. Omit a section only if empty.
- **Workstreams** a **bold single-line** label (`**PR #106538 — …**`, `**RHJ**`),
  ordered by importance. Never `####`. Any sub-label below a workstream is also a
  bold line, never a heading.
- **Checkboxes for to-dos** in **Handover**, write each *actionable* item (a thing
  the next session must DO — post a draft, re-pin cores, decide X, cherry-pick Y)
  as a `- [ ]` checkbox so Notion makes it a to-do block. Leave purely
  informational Handover lines — branch/commit state, file / harness / binary
  locations — as plain `-` bullets. **Done** items are all plain `-` bullets.
- **Handover** captures what the next session needs: paste-ready drafts as
  blockquotes, ⚠️ machine-left-non-default warnings with teardown steps, pending
  decisions, perf/optimization follow-ups worth trying, and the locations of bench
  harnesses / scripts / frozen binaries (with sizes and timestamps) and branch
  state (branch, HEAD sha, pushed?, tree clean?).
- **Done** captures what shipped: committed + pushed work (name the branch),
  correctness verification (tests green, row counts), benchmark tables with
  speedups, root-caused bugs, and reusable tooling built.
- Be specific and quantitative; prefer tables for benchmark numbers. Keep only
  load-bearing detail. Do not invent numbers — if a value isn't in the transcripts
  or verification, say so.

### 7. Mark the run

After the note is composed, record the invocation time so the next default
window starts here. Do this LAST, so a failed run doesn't lose the window.
The state is shared: marking from Cursor or Claude Code advances the same
window.

```bash
python3 ~/brain-dump/scripts/list_sessions.py --mark-run
```

## Output example

This is the target format and level of detail. Emit just the markdown shown
between the fences below — the surrounding ` ```markdown ` fence is only so the
example displays in this doc; **do not reproduce that fence in your output** (the
note must be plain markdown, not a code block):

```markdown
## June 8, 2026

### Handover

**PR #106538 — `IColumn::computeHashInto` hash kernel for sharded aggregation**

- [ ] Paste the Cloud Performance Report reply (draft below) into the PR comment thread on #106538
- [ ] Cherry-pick the reverted scatter/batching work (`ColumnsScatter`) into **icolumn-shuffle-primitives**

> Re-tested locally after making `computeHashInto(initial=false)` match the old `WeakHash32::update` composition semantics bit-for-bit.
>
> Setup: baseline = PR merge-base; candidate = current HEAD; ClickBench `hits`; `warmups=1`, `tries=9`; `max_threads=4`; `enable_sharding_aggregator=1`; `FORMAT Null`.
>
> | report id | baseline median | candidate median | change |
> | --- | --- | --- | --- |
> | q16 | 0.488s | 0.452s | -7.4% |
> | q34 | 4.030s | 3.304s | -18.0% |
>
> Conclusion: I can no longer reproduce the reported regressions locally.

- Benchmark scripts: all tooling lives under `tmp/`; frozen binaries are `tmp/clickhouse_baseline` and `tmp/clickhouse_candidate` (both 4.6 GB, June 8 timestamps)

**RHJ**

- [ ] Decide: keep RapidHash given neutral perf, or revert to the two-hash design / try the hybrid — raise with team before further build
- [ ] ⚠️ Machine left non-default: cgroup v2 `cpuset` partition `/sys/fs/cgroup/bench` is **still active** — CH server pinned to cores 0–19. Tear down (move CH back to root cgroup, `rmdir /sys/fs/cgroup/bench`, restart via `start.sh`) before other work or it'll skew unrelated runs.
- [ ] Perf follow-up worth trying: hybrid hash — keep hardware CRC32C for routing, use RapidHash low bits only for the bucket
- Branch state: `phj4`, HEAD `da6e279` (RapidHash) committed + pushed; working tree clean
- Optimization target: Q8 / wide probe-projection joins are gather-bound (~1.1×) — the output gather path, not the hash, is the bottleneck
- Bench harness (all in `tmp/`): `chj_vs_rhj.sh`, `rhj_perf_ab.sh`, `rhj_correct.sh`. Server: `tmp/bench-server/{start,stop,reload_data}.sh` (Memory-engine, reload after every restart)

### Done

**RHJ**

With `RapidHash`, isolation and max_threads = 16:

| Q | CHJ (ms) | RHJ (ms) | Speedup (CHJ/RHJ) |
| --- | --- | --- | --- |
| Q1 | 791 | 433 | 1.83× |
| Q8 | 615 | 576 | 1.07× |
| **Total** | **7034** | **4969** | **1.42×** |

- RHJ wins all 9; overall **1.42×**. Q8 (gather-bound, widest probe projection) remains narrowest at 1.07×.
- Shipped: single 64-bit RapidHash unification (committed + pushed, branch `phj4`). High bits route the scatter/leaf, low bits index the bucket. Removes the ~2³¹-row saturation limit.
- Correctness verified: all 36 RHJ unit tests green; all 9 end-to-end join queries return exactly 100M rows.

**PR #106538 — `IColumn::computeHashInto` hash kernel for sharded aggregation**

- Replaced the per-chunk allocating `getWeakHash32` path in `BufferedShardByHashTransform` with a non-allocating per-row `computeHashInto` + `mapToRange` kernel.
- Root-caused a regression on 5 high-cardinality `GROUP BY` ClickBench queries to a change in multi-column hash composition; fixed by making `computeHashInto(initial=false)` match the old `WeakHash32::update` bit-for-bit.
- Local re-run shows no regressions (worst case ±0.7%); 3 of 5 are improvements (−7% to −18%).
- Built a reusable per-query A/B harness (`tmp/bench_106538.py`) for future profiling.
```
