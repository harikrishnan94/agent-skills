# Observer

Requires Python 3, authenticated `gh` with `api --paginate --slurp`, and a POSIX
host (Linux/macOS). Run it from this skill's own directory, the directory this
SKILL.md was loaded from (e.g. `~/.claude/skills/watch-pr`,
`~/.codex/skills/watch-pr`, `~/.cursor/skills-cursor/watch-pr`, or
`~/.copilot/skills/watch-pr`). The examples write `<skill-dir>` for that path;
substitute the real one. A symlinked skill directory works as is.

One observation:

```bash
python3 <skill-dir>/scripts/observe_pr.py "$PR_URL" --state-dir "$STATE_DIR/observer"
```

Quiet polling in a supported background monitor:

```bash
python3 <skill-dir>/scripts/observe_pr.py "$PR_URL" --state-dir "$STATE_DIR/observer" --watch --interval 120
```

The observer never mutates GitHub, invokes an agent, posts text, or repairs code.
The caller owns wakeups, schedule, permissions, failure attribution, and completion.

## What it collects

Every observation reads the PR, its issue comments, inline review comments, and
reviews, plus the check runs, commit statuses, and Actions runs of the PR head
commit, whether the PR is open, closed, or merged. CI attaches to the head commit
only; GitHub's test-merge commit never carries any, so it is not queried. Its SHA
and the mergeability verdict travel in the `pr` source.

GitHub computes mergeability lazily: the first read of a cold PR reports `null`.
The observer re-reads the PR a few times, two seconds apart, before collecting,
and records `null` only when it never settles. After collecting, it re-reads the
PR once more and repeats the whole collection if the head or state moved
meanwhile, or if a paginated listing grew under it; it makes up to three attempts.
Comment, label, and title churn during collection does not invalidate it.

## What it writes

`sources/<sha256>.json` holds each source's content as compact JSON named by its
hash, written once; an unchanged source is never rewritten. `events.jsonl` gains
one line per changed observation, with `observed_at`, `snapshot_id`, the
`changed` source names, and the `sources` name-to-hash map, appended before
`latest.json` advances. `snapshot_id` is derived from the source hashes, so a
replay after an interruption produces the same id: skip an event whose
`snapshot_id` matches the last one processed. `latest.json` records the last
successful poll time and the current hashes. In watch mode a failed poll appends
`{"event": "observation_error", ...}` to `events.jsonl` as well.

## Output and exit codes

Single-observation mode prints one JSON result: `event` (`changed` or
`unchanged`), `changed`, `snapshot_id`, `sources` (name to file path), `state`,
`merged`, `head`, `base`, `mergeable`, `mergeable_state`, `github_ci_rows`,
`github_ci_terminal`, `failures`, and `action_required`. Watch mode prints only
changed observations and stops after observing a closed or merged PR.

Rows come from three levels: `status`, `job` (a check run), and `run` (an Actions
workflow). A run only aggregates its jobs, so runs count only while no job has
appeared yet. `github_ci_terminal` is true when every counted row has finished.
`failures` lists finished rows whose conclusion is not `success`, `skipped`, or
`neutral`, each with its raw `outcome`. `action_required` rows are listed apart:
they mean a run awaits approval, which is a merge blocker rather than a defect.

Exit 0 means observation succeeded, never that CI passed. Exit 1 is an error,
reported on stderr as `{"event": "observation_error", "error": ...}`. Exit 3 is
`observer_busy`: another watcher already owns this state directory. In watch mode
a transient `gh` failure or a collection race is logged and retried with growing
backoff, and the process exits 1 after five consecutive failures. A schema error
or a state directory that belongs to another PR is fatal in both modes.

Observations are serialized: a one-shot read waits up to a minute for a running
watcher's poll to finish, and the watcher releases the lock while it sleeps. Only
one `--watch` process may own a state directory. Monitor termination or task
cancellation ends observation; no autonomous service is installed. The lock does
not establish ownership of the PR worktree.

## Limits

`github_ci_terminal` describes the observed GitHub rows only. Even when true, failed
rows can remain, required jobs may not have appeared yet, or an external report may
still be incomplete. Review-thread resolution and branch-protection requirements
must be checked separately. Fork-only checks and provider-specific pipelines may
require an additional source. The agent must establish complete relevant coverage
before issuing `CLEAN` or `SETTLED_WITH_UNRELATED_FAILURES`.

GitHub's [check-run endpoint](https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference)
limits the suites it examines on extremely busy revisions. Its
[combined-status endpoint](https://docs.github.com/en/rest/commits/statuses#get-the-combined-status-for-a-specific-reference)
returns the latest legacy status per context. The
[PR endpoint](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request)
reports unknown mergeability as null; that is not a clean result.
