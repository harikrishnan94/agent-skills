---
name: watch-pr
description: Watch a GitHub pull request through CI rounds, resolve conflicts, fix PR-caused failures, validate and push authorized changes, and preserve state for handoff to another agent. Use when asked to watch a PR, keep it healthy, or resume an existing PR watcher.
---

# Watch a pull request

Keep the named PR healthy while preserving its design and test coverage. Work
through observation, attribution, repair, and verification of the pushed revision.

## Establish the assignment

Resolve the PR URL, live head and base, push repository/branch, and worktree.
Never assume `origin` is upstream or that the current checkout contains this PR.
Use an existing assigned worktree, or create an isolated one under repo conventions.
Only one agent may modify a PR worktree; coordinate before taking over an active owner.

Preserve the user's authorization across rounds and handoffs. A request to watch
and fix a PR covers the work necessary to prepare the fixes. Honor any existing
authorization to commit, push, or merge the base without asking again. Otherwise
prepare and verify the exact change before requesting the missing authorization.
Posting content, changing another repository, replacing/closing the PR, and merging
the PR require authorization for those actions. The emoji rule below grants none.

Default to stopping when the current revision is settled. Use continuous watching
until closure or merger when requested. Record timezone, quiet hours, and any work
pause separately: silence over a weekend does not itself suspend repair work.
Apply an existing deadline or budget; do not invent a new one.

For ClickHouse, read [references/clickhouse.md](references/clickhouse.md).

## Attribution on GitHub posts

**Prefix every GitHub post containing content not written by the user with exactly
`🕵️ `, including the space.** This covers comments, inline reviews, replies, and
PR/issue titles and bodies. Mark each independently posted item, not just the first
item in a batch. This rule does not apply to commit messages.

- Generated, summarized, translated, polished, and mixed user/agent text need the prefix.
- User approval of an agent-written draft does not make it user-authored. Keep the prefix.
- Only text written by the user and posted verbatim is exempt. Supplying text
  does not itself establish authorship. Use the prefix when authorship is uncertain.
- For attachments or other non-text output, mark the accompanying title, caption,
  or message with `🕵️ `.
- Editing an existing item with agent-written text requires the prefix on that item.
  Preserve its history and meaning. Do not rewrite unrelated historical posts.
- Keep an existing `🕵️ ` prefix once. Do not substitute a different detective emoji.
- This explicit user convention overrides generic style guidance against emoji.

Prepare the exact payload, including its prefix, before any required approval.
Immediately before posting, check authorization, destination, authorship, and prefix.
Keep a posted item's URL/ID in state to avoid duplicate replies on resume. If a write's
result is uncertain, inspect the destination before retrying.

## State that travels with the PR

Keep a directory under the main checkout's conventional scratch location, normally
`tmp/pr-watch/<host>/<owner>/<repo>/<number>`. Keep it out of commits and record its
absolute path in the agent's required working-state file.

Maintain one current `STATE.md` with:

- Assignment, permissions, owner, worktree, push target, stop condition, and schedule.
- Head/base SHAs, current round/phase, and the latest observation processed.
- Findings by signature: classification, affected revision/run attempt, evidence,
  fix commit, and outstanding verification. Include unresolved review requests.
- Owned processes, monitor lifetime, posted-item IDs, and the exact next action.

Rewrite stale sections after each completed step. Retain raw logs and observations
separately. Do not turn `STATE.md` into an accumulating transcript.

On resume, first read the host's required working-state file, then reconcile this
handoff with live state. Do not inherit shell variables or assume a monitor survived.
Before transferring ownership, checkpoint pending work and release the prior owner.
The new owner must verify live state and restart observation before making changes.

## Observe every blocking signal

Use the bundled observer; read [references/observer.md](references/observer.md) for
its commands, outputs, and limits. It only reads GitHub and writes local evidence.

Observe lifecycle, head/base movement, mergeability, checks, commit statuses,
workflow runs, and discussion/review comments, including edited bot reports.
Read linked CI reports too: a GitHub status may summarize hundreds of external jobs.
Inspect unresolved review threads through the provider's API before claiming review
coverage; a list of comments does not establish their resolution status.

Keep observations separate from repair decisions. Empty checks, API failures,
`UNKNOWN` mergeability, and a successful observer exit are not evidence of success.
Do not suppress entire checks such as `CH Inc sync`. Revalidate specific prior
classifications when the revision, run attempt, failure signature, or relevant code changes.

Run the observer in the host's supported monitor or external runner and record its
lifetime. The script cannot wake an agent after that host terminates it. Emit user
notifications only for actionable changes, completion, failure, or required decisions.
Record API errors and re-establish observation; never remain silently blind.
While external CI is still running, revisit its reports even if GitHub metadata is unchanged.

## Analyze and repair a round

Use a fresh analysis subagent for each round requiring attribution. Give it the PR
intent, pinned revisions, failure inventory, logs, and scope. Require a compact
finding per failure: signature, classification, evidence, proposed fix, and exact
validation commands. Keep build/test output in log files and delegate verbose log
analysis. Follow any stricter repository requirements.

For each finding, first ask whether the same failure is also true on the target
branch (`master` in ClickHouse). Check the actual signature, exercised code, and
configuration. A matching test name or historical flake rate is insufficient.
Record unrelated failures with evidence and skip their repair. Mark unresolved
attribution `UNSETTLED`; do not convert uncertainty into an exemption.

Before editing, record the suspected cause, reproduction command, and expected
result. Reproduce before and after when possible; run relevant regression checks.
Compilation alone does not prove a behavioral fix. If the needed architecture or
sanitizer is unavailable locally, record that gap and require the matching CI result.

Preserve the PR's design and motivation. Do not weaken tests to obtain green CI.
A defective assertion can be repaired only with evidence for the correct invariant
and a check that the replacement still detects the behavior it is intended to test.
Surface material design changes for a decision while continuing independent work.

Before committing, run the repository's style checks and these sibling skills:
[humanize](../humanize/SKILL.md), [plain-prose](../plain-prose/SKILL.md), and
[reduce-complexity](../reduce-complexity/SKILL.md). Resolve their paths from this
skill's real location, not the caller's working directory. An unavailable required
pass remains unmet unless the user has accepted equivalent instructions.

A verifier must independently check fixes and final failure classifications,
including rounds with no patch. It must not have produced the artifact or
classification being checked. If independent execution is unavailable, report
that requirement as unmet rather than claiming an independent review.

## Publish authorized fixes

Use new commits. Never amend, rebase, force-push, or commit on the base branch.
Stage explicit paths and inspect both the staged diff and the complete PR diff.
Account for changes introduced by a deliberate base merge; preserve remote history.
Do not sweep local submodule drift or another agent's changes into the commit.

Immediately before pushing, fetch the exact PR branch and resolve its fetched tip
as `REMOTE_HEAD`. Run `git merge-base --is-ancestor "$REMOTE_HEAD" HEAD`; require
exit 0. If it fails, reconcile the concurrent change and repeat affected validation.
Push without force, verify the resulting remote SHA, and observe that revision's CI.

Apply the repository's PR template to authorized PR updates and retain required
commit trailers.

## Completion

Collect a fresh observation before and after checking the final CI evidence.
Require unchanged head/base SHAs and confirmed mergeability for an open-PR verdict.
Explain any other merge blocker; a `BLOCKED` status alone does not explain its cause.

Require a complete, terminal CI execution for the current revision. Account for
expected jobs, explain skips, and validate actual report coverage. Use the newest
applicable run attempts; do not count a superseded failure as a current failure.
Record each fix's exact reproduction/regression commands, results, and evidence paths.

- `CLEAN`: applicable CI passed, mergeability is confirmed, and every investigated
  issue has a disposition. List remaining human review or external requirements.
- `SETTLED_WITH_UNRELATED_FAILURES`: remaining CI failures have specific evidence
  that this PR did not cause them. List each failure and any separate merge blockers.
- `UNSETTLED`: attribution, coverage, verification, or a required decision remains
  incomplete. State what would settle it and preserve the next action.

Do not declare completion until the gates and independent verification pass.
Pushing, timing out, or exhausting a budget does not satisfy them. In continuous
mode, a settled revision returns to quiet waiting. Closure/merger stops the watcher
without authorizing that action. Finish with the exact commits, verification limits,
remaining blockers, and handoff path.
