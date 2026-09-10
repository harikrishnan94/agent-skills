---
name: watch-pr
description: Keep a GitHub PR green while preserving its motivation. Diagnose CI blockers, resolve merge conflicts and ClickHouse private sync, validate authorized fixes, and retain state for unattended watching or handoff.
---

# Watch a pull request

Preserve the PR's intended benefit and account for every applicable CI job.
A diagnosed failure remains a blocker until recovered or explicitly handed off.

## Assignment and intent

Resolve live head/base, exact push repository/branch, and assigned worktree.
Never assume `origin` is upstream. Isolate work when needed; only one repair
owner may modify the worktree. Observer locks do not establish that ownership.

Carry existing authority for commits, pushes, base merges, reruns, and private
sync repairs across rounds and handoffs. Prepare and verify a concrete action
before asking for missing authority. Posting, changing another repository,
replacing/closing the PR, and merging the PR need their own authority.
Before drafting GitHub content, read [posting.md](references/posting.md).

Default to watching until the current revision is green or needs external action.
Continuous mode watches until closure/merger. Honor existing budgets, deadlines,
quiet hours, and pauses; silence does not itself pause repair work.

Before editing, record intent from the author's description, linked issue,
decisions, tests, and code: the problem, intended benefit, chosen approach and
why it matters, behavior/compatibility/performance invariants, coverage, non-goals,
and evidence distinguishing the benefit from pre-PR behavior. Retain this across
repairs. Reconcile author changes explicitly; never rewrite intent to justify a
fix. Investigate ambiguity, then request only the needed decision while
continuing independent work.

## Durable, economical observation

Keep evidence outside commits under the main checkout's scratch location,
normally `tmp/pr-watch/<host>/<owner>/<repo>/<number>`. Record its absolute path
in the handoff and host-provided agent-memory working-state file, when present.
Maintain a compact `STATE.md`: assignment/authority, intent, owner/worktree,
head/base/test-merge SHAs, expected CI, blocker signatures and evidence, fixes and
validation, processed event, monitor lifetime, and exact next action. Rewrite
current state; retain raw logs separately.

Use the bundled [observer](references/observer.md). Poll without an LLM turn per
poll. Before unattended watching, verify the host's wakeup/restart mechanism
handles events, process exit, and stale observation. Record who checks
`latest.json.observed_at` and when it next runs. A subprocess cannot wake an
agent or restart itself. If no durable runner exists, disclose that limit and
leave a concrete continuation; never claim unattended watching is active.

Read compact summaries and changed sources first. Fetch full logs only for new
or changed failures. Reuse classifications while intent, exercised code,
configuration, revision applicability, and signature remain valid. A new attempt
needs fresh results, not automatic reanalysis of the PR. Delegate only substantial
new attribution/log work with bounded evidence; request cause, fix, validation,
and paths. Do not spawn agents or repeat quality passes on unchanged polls.

Observe revisions, mergeability, checks, statuses, workflows, and edited bot/review
reports. Revisit pending external reports at a recorded cadence even without
GitHub changes. Notify only for actionable changes, completion, monitor failure,
or required decisions. On resume, read host working state then `STATE.md`,
reconcile live state, verify evidence, and restart observation. Checkpoint and
release the old repair owner before transferring ownership.

## Account for every blocker

For ClickHouse, read [clickhouse.md](references/clickhouse.md).

Establish expected CI from effective branch rules, workflow/CI plans, changed
paths, and provider reports. Track required checks separately from other applicable
jobs. Persist GitHub expectations in the observer's `requirements.json`; refresh
for revision/configuration/rule changes. Inspect review-thread resolution and
other merge requirements through the provider API. Missing access or coverage
remains unknown. Reconcile expected and observed jobs before completion.

Each blocker needs revision/run attempt, signature, evidence, cause, next action,
and verification. Follow [blocker actions](references/observer.md#blocker-actions)
for missing, pending, skipped, cancelled, approval, and infrastructure states.
Never suppress entire checks such as `CH Inc sync`.

Compare the exact failure against the target branch in the same configuration.
A matching test name, flake history, timeout, or disjoint changed files does not
establish causation. Keep uncertain attribution `UNSETTLED`. Unrelated defects
need no speculative patch in this PR, but still need authorized CI recovery or an
explicit external blocker with an owner/next action.

Before rerunning, record why retry can help and which attempt it replaces. Retry
the smallest affected scope and inspect its result before another retry. Repeated
identical failure without new evidence requires diagnosis or escalation, not
retries until green. Inspect uncertain mutation results before retrying.

## Repair while preserving intent

Before editing, record cause, reproduction, expected result, and affected intent
invariants. Make the smallest adequate fix. Demonstrate both that the failure is
repaired and the original benefit survives. For performance changes, verify the
changed path executes and use valid benchmark controls; correctness alone is
insufficient. Never obtain green CI by reverting/bypassing the intended change,
disabling coverage, loosening limits, or weakening assertions. Repair a defective
assertion only with evidence for the correct invariant and a check that still
catches the defect. Escalate unavoidable design tradeoffs, continuing independent work.

Match the failing architecture, sanitizer, and configuration. Record unavailable
local checks and require matching CI results; compilation alone is insufficient.

For conflicts, merge the freshly fetched target base as a new merge commit; never
rebase. Pin the common ancestor and both parents. Establish each side's intent
and record how the resolution preserves both; never choose `ours`/`theirs`
wholesale. Handle rename/delete, generated files, and submodules explicitly.
Review interacting cleanly merged files too. Check for unmerged entries and
conflict markers, rebuild affected targets, and test combined behavior plus the
original benefit. Apply these semantic checks to clean base updates required by
CI too. Reconfirm head/base and invalidate affected evidence after concurrent changes.

## Validate and publish

On the fix's own diff, apply repository style plus humanize, plain-prose, and
reduce-complexity. Load these skills once and scope edits to the fix's hunks;
report unrelated author-code findings without editing. If the host cannot load
them, use their sibling directories beside this skill. An unavailable required
pass remains unmet unless the user accepts equivalent instructions.

After all editing passes, validate the final tree. Record commands, configuration,
results, log paths, and tested tree/commit; further edits invalidate affected
checks. An independent verifier must check fixes, intent preservation, and final
failure dispositions it did not produce. Reuse its verdict only for unchanged
evidence/scope. Report an unavailable independent check as an unmet gate.

Use new commits; never amend, rebase, force-push, or commit on the base branch.
Stage explicit paths, inspect staged and full PR diffs, and exclude unrelated work
or submodule drift. Preserve required trailers and templates. Immediately before
pushing, fetch the exact PR branch as `REMOTE_HEAD` and require
`git merge-base --is-ancestor "$REMOTE_HEAD" HEAD` to exit 0. Otherwise reconcile
and revalidate concurrent changes. Push without force, verify the remote SHA,
and observe that revision's CI.

## Completion

Observe immediately before and after final evidence review. Head, base,
test-merge identity, relevant attempts/results, and merge requirements must remain
consistent. Require full applicable CI/report coverage, explained skips, preserved
intent, semantic merge validation, independent verification, and current CH sync
when applicable. Successful observer exit or terminal rows alone proves none of these.

- `GREEN`: applicable CI passed or has justified permitted skips; intent and
  verification gates passed. List remaining human/merge requirements separately.
- `BLOCKED`: identified external action/decision needed. Give evidence, owner or
  destination, next action, and resume trigger. This is not success.
- `UNSETTLED`: investigation, coverage, or verification incomplete. Continue within
  the assignment or checkpoint an exact continuation at its limit.

Unrelated failures never count as green. Explain merge blockers rather than
merely echoing `BLOCKED`. Continuous mode waits quietly after green and resumes
blocked work on its trigger. Closure/merger stops watching without authorizing
that action. Finish with exact commits, verification limits, blockers, and handoff path.
