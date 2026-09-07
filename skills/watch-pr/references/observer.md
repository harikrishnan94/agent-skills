# Observer

Requires Python 3, authenticated `gh` with `api --paginate --slurp`, and a POSIX
host (Linux/macOS). Locate the script relative to the real `watch-pr` directory.

One observation:

```bash
python3 "$WATCH_PR_SKILL/scripts/observe_pr.py" "$PR_URL" --state-dir "$STATE_DIR/observer"
```

Quiet polling in a supported background monitor:

```bash
python3 "$WATCH_PR_SKILL/scripts/observe_pr.py" "$PR_URL" --state-dir "$STATE_DIR/observer" --watch --interval 120
```

Set `WATCH_PR_SKILL`, `PR_URL`, and `STATE_DIR` to their resolved paths/value first.
The observer never mutates GitHub, invokes an agent, posts text, or repairs code.
The caller owns wakeups, schedule, permissions, failure attribution, and completion.

The observer paginates GitHub check runs, commit statuses, Actions runs, issue
comments, inline review comments, and reviews. It observes the PR head and, when
GitHub confirms mergeability, the current test merge commit. If PR metadata changes
during one collection, it repeats the collection up to three times and then fails.
API/schema failures propagate and leave the last successful observation intact;
restart after diagnosing the failure.

Each changed observation is saved under `snapshots/`. `events.jsonl` records the
changed sources and snapshot path before `latest.json` advances. Replayed events
after interruption can be duplicates; use the snapshot ID and the agent's last
processed event to avoid repeating work. `latest.json` also records the last
successful poll time. A process lock prevents two observers writing the same directory.
This lock does not establish ownership of the PR worktree.

Single-observation mode always prints a compact JSON result. Watch mode prints
only changed observations; closure or merger stops it. A script exit of 0 means
observation succeeded, never that CI passed. Errors exit nonzero. Monitor termination
or task cancellation ends observation; no autonomous service is installed.

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
