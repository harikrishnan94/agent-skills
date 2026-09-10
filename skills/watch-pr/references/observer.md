# Observer

Requires Python 3, POSIX (Linux/macOS), and authenticated `gh` supporting
`api --paginate --slurp`. Resolve `<skill-dir>` from this skill's installed
location, including symlinks; never from the caller's working directory.

```bash
python3 <skill-dir>/scripts/observe_pr.py "$PR_URL" --state-dir "$STATE_DIR/observer"
python3 <skill-dir>/scripts/observe_pr.py "$PR_URL" --state-dir "$STATE_DIR/observer" --watch --interval 120
```

The observer only reads GitHub and writes local evidence. The caller owns
permissions, external reports, repair, completion, and a durable wakeup mechanism.

## Coverage and requirements

Each poll reads PR metadata, discussion, inline comments, reviews, checks,
statuses, and workflow runs. CI is collected for both head and current test-merge
SHA when available. GitHub can require [test-merge checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks).
Do not treat all head and merge rows as interchangeable: establish which revision
and source each expected job must test, and explain inapplicable rows explicitly.

Unknown mergeability gets five reads, two seconds apart. A collection repeats up
to three times if lifecycle, head/base identity, mergeability, test-merge SHA, or
pagination coverage changes. Comment/title/label churn does not invalidate CI
collection; decision-relevant edits are captured on the next poll.

Workflow rows remain visible even when jobs exist. For automatic push, PR, and
merge-group events, only the newest run per workflow ID/event/branch/fork is
summarized, keeping different PR identities separate. Checks belonging to known
superseded suites are excluded. Manually
triggered runs remain separate because their inputs may differ. Raw sources
retain all attempts; inspect them when applicability is ambiguous. Do not group
by display name or combine a new pending attempt with an old passing verdict.

Once expected GitHub jobs are established from effective rules and CI plans,
atomically write `observer/requirements.json` (names below are illustrative):

```json
{
  "head": "HEAD_SHA",
  "base": "BASE_SHA",
  "test_merge_sha": "TEST_MERGE_SHA",
  "checks": [
    {"source": "checks:HEAD_SHA", "name": "build", "app_id": 15368},
    {"source": "statuses:HEAD_SHA", "name": "CH Inc sync"}
  ]
}
```

Use JSON `null` when there is no test-merge SHA. Sources are `checks:SHA`,
`statuses:SHA`, or `workflows:SHA`; use the actual applicable SHA. `app_id` is
optional and pins a required check to its expected GitHub App. A check and status
with the same required name need separate entries. Include all known applicable
GitHub jobs; track external coverage and permitted exclusions in `STATE.md`.

`requirements_current` is false if the file is absent or its revisions differ.
When current, `missing_required` lists expectations without matching rows.
These are presence checks, not a green verdict: require current expectations,
no missing entries, successful applicable results, justified skips, and complete
external evidence. An incomplete inventory cannot establish coverage merely by
being revision-current. Refresh expectations when rules/configuration change;
retain unchanged entries to avoid repeatedly rediscovering CI.

## Blocker actions

| Signal | Action and evidence needed |
| --- | --- |
| Failed build/test/style/performance | Diagnose the exact signature; repair within intent; reproduce and verify the applicable CI configuration. |
| Missing or unexpected skip/neutral | Inspect required rules, trigger/path/label conditions, CI plan, and upstream dependencies. Repair/retrigger when authorized; justify any exclusion. Never disable a gate to satisfy it. |
| Queued/pending/waiting | Identify runner, dependency, approval, or external job and last progress. Record when to revisit; investigate stagnation against that job's normal runtime. |
| Cancelled/stale/timed out | Establish whether superseded, intentional, infrastructure, or a regression. Recover only the applicable revision and attempt. |
| Approval/action required | Identify the required actor and action. Preserve a blocked resume trigger; do not treat it as a code defect or bypass trust checks. |
| Infrastructure/flaky | Require signature/configuration evidence. Retry the smallest scope only when justified; persistent identical failure without new evidence needs escalation. |
| Stale external status or sync | Inspect the actual producer and tested revisions; verify status propagation. A stale summary is not a reason to patch code. |
| Unknown/API/access failure | Restore observation/access or report the external dependency. Empty results never establish success. |

## Evidence and compact output

`sources/<sha256>.json` holds complete raw sources. Publication is atomic;
subsequent observations verify existing bytes and repair interrupted legacy writes.
`events.jsonl` records changed observations before `latest.json` advances. Events
include source hashes and a content-derived `snapshot_id`; deduplicate an immediate
replay against the last processed event, not against every historical ID. Advance
the consumer cursor only after recording the decision/next action in `STATE.md`.

`latest.json` records the last successful poll time, snapshot, raw source hashes,
and signal hashes. Timestamp-only `updated_at` changes retain fresh evidence but
do not produce an event. Edited content, status, IDs, and run attempts still do.
Raw evidence is stored locally; do not load whole snapshots into agent context.

One-shot mode prints one JSON result; watch mode prints only meaningful changes.
Results contain revision/merge state, source paths, `github_ci_rows`,
`github_ci_terminal`, `requirements_current`, and blocker lists: `failures`,
`action_required`, `pending`, `skipped`, `missing_required`. Each list has a total
`*_count` and at most 20 printed entries. If a count exceeds the printed length,
inspect the linked raw sources to cover the remainder. Never silently drop them.

`github_ci_terminal` means only that observed current rows finished, even if they
failed or expected jobs never appeared. Required-rule discovery, review-thread
resolution, merge queues, fork-only pipelines, private sync, and external report
coverage still need provider-specific evidence. GitHub's check-run endpoint limits
examined suites; workflow searches cap results at 1,000. Incomplete pagination
is an error, not a clean result.

## Lifetime and recovery

Exit 0 means observation succeeded; 1 means error; 3 means observer busy. Errors
are JSON on stderr. Watch mode also appends transient API/race errors to the
event log, retries with bounded backoff, and exits after five consecutive failures.
Invalid schemas/state are fatal. The watcher serializes polls, permits one watch
process per state directory, and stops when the PR is closed/merged.

Configure the host supervisor to wake on changed events and exits and to check
freshness even when stdout is quiet. Allow for collection/backoff when setting
staleness limits. Repeated failure needs access/provider diagnosis, not an endless
restart loop. Verify the monitor's PID/job identity and last successful poll on
resume. An observer lock is not a repair lease. Preserve a single repair owner.

A one-shot read during quiet polling must not consume an event on behalf of the
agent: process unacknowledged events from `events.jsonl`, not just fresh stdout.
Record a separate cadence for pending external reports and blocked resume triggers.
No service or scheduler is installed by this script.
