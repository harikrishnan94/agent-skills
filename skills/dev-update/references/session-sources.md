# Session collection

Resolve the real path of this skill first: installations can be symlinks.
Its sibling `brain-dump/scripts/` contains `list_sessions.py` and
`condense_session.py`. Verify both exist on each host. Do not copy a path
from localhost into a remote command without checking it there.

The known source checkouts are `/Users/hari/projects/agent-skills` locally
and `/home/ubuntu/agent-skills` on dev. These are discovery hints, not fixed
requirements. On dev the latter currently resolves under `/mnt/ch/projects/`.

## Inventory and index

Check each store independently on each host. Record readable, empty, missing,
or failed; a missing directory is not proof of no work. The reader supports:

| Tool | Store under that host's home directory |
| --- | --- |
| Claude Code | `.claude/projects/*/*.jsonl` |
| Codex | `.codex/sessions/**/rollout-*.jsonl` |
| Cursor | `.cursor/projects/*/agent-transcripts/*/*.jsonl` |
| Copilot CLI | `.copilot/session-state/*/events.jsonl` |

Inspect alternate stores when present: Codex `archived_sessions`, Cursor
text transcripts or IDE databases, and cloud/worktree sessions that may not
have been mirrored locally. The default reader only covers the patterns
above. Use another available read-only reader or report a coverage gap;
never claim all sessions were read based only on a successful default scan.

Run the existing index on each host with explicit offset-aware timestamps:

```text
python3 <brain-dump>/scripts/list_sessions.py 
  --since <posted_at> --until <collected_at> --include-empty
  --exclude-session <current-session-id> --json
```

The line breaks above are illustrative; pass the arguments as one command.
Run the remote equivalent through `ssh dev`, quoting paths and arguments.
Read metadata and relevant excerpts remotely; do not copy whole private
session stores to localhost. Scratch indexes/excerpts may live in the task's
work directory. Do not use `--mark-run` or write `~/.brain-dump/last_run`.

Always pass `--include-empty`: some current Codex recordings store human
prompts as `response_item` messages without `event_msg/user_message`, and
the old index reports zero user turns for them. Zero turns does not mean an
empty session. Index overlap can also be caused by file modification time,
so it is a candidate filter, not dated evidence of work.

Keep the exact host, source, session ID and path with each candidate.
Inventory all candidates, then inspect relevant work; do not stop after the
first few sessions or search only PR numbers already listed in Notion.
Exclude personal work and pure approval-review/helper sessions, but follow
a helper result when its parent needs it to substantiate a claim.

## Read activity

Use `condense_session.py <path> --no-tools --max-chars 12000` for an initial
read. The cap retains the tail and may omit earlier in-window work. Read
omitted ranges when needed; never turn a truncated scan into a completeness
claim. Condensed turn headers can reflect the user prompt's time, while a
result arrives later. Check raw event timestamps for boundary cases.

For modern Codex recordings, inspect `response_item` user messages when
`event_msg/user_message` is absent. Discard injected environment/AGENTS
content and copied history. Assistant `output_text` messages and captured
tool results can establish what happened, subject to verification. An
approval-review session repeats another session's prompts and is not an
additional workstream. Compare parent/session identity before deduplicating.

Use raw UTC timestamps to compare events across hosts. Do not infer activity
from mtime, title, compaction time, replayed history, or a copied session.
Deduplicate mirrors by session identity plus matching events; if copies have
diverged, retain the union of distinct in-window activity. Search a relevant
parent's subagent records only when they add missing evidence.

Build a compact evidence table in working context or scratch storage:

| Item | Dated activity | Source pointer | Issue/PR | Verified state |
| --- | --- | --- | --- | --- |
| Workstream | Actual action/result time | Host + session + event, or dated Notion/GitHub entry | Canonical URL | Only claims needed in draft |

Keep plans, inferred associations, stale states and inaccessible sources
out of the verified columns. Fetch issue/PR identity and status once per
item, reusing those results during the draft. Re-read only when the data has
changed or a specific uncertainty remains.
