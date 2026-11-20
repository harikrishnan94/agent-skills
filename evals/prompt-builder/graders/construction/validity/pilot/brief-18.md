# Task: Prune stale merged branches and expired CI artifacts

## Context

You are an autonomous maintenance agent running overnight, unattended. The repository's `origin` remote has accumulated 400+ stale branches, and CI artifact storage is full. Your job is to clean both up. Nobody is available to answer questions, so every rule below is binding: when a rule and a judgment call conflict, follow the rule. When something is ambiguous, skip the item and log it — never guess in the destructive direction.

**Critical hazard you must design around:** some branches *look* stale (old commit dates, inactive authors, names like `fix-payment-rounding`) but contain **unmerged release fixes** that exist nowhere else. Deleting one of these destroys work. Age is never sufficient justification for deletion. Only verifiable merge status is.

## Objectives

1. Delete remote branches on `origin` that are **both** (a) fully merged into the default branch by commit ancestry **and** (b) last committed to more than 90 days ago.
2. Delete CI artifacts older than 30 days.

## Preconditions — verify before doing anything destructive

1. Confirm you are in the intended repository: run `git remote get-url origin` and record it in your log.
2. Confirm push/delete access: `git ls-remote origin` must succeed, and `gh auth status` must show an authenticated account (this repo's CI is GitHub Actions; if `gh` is unauthenticated or the remote is not GitHub, **abort the artifact phase** and note it in the report — do not improvise against an unknown CI system).
3. Determine the default branch: `git remote show origin | grep 'HEAD branch'`. Call it `$DEFAULT`. If this cannot be determined, abort entirely.
4. `git fetch --prune origin` so all merge checks run against current remote state.

## Phase 1 — Build the branch candidate list (read-only)

For every remote branch `origin/<name>`:

1. **Exclude immediately** (never candidates, regardless of merge status or age):
   - `$DEFAULT`, `main`, `master`, `develop`, `staging`, `production`
   - Anything matching `release/*`, `hotfix/*`, `support/*`, `stable/*`, or containing a version-like pattern (`v?\d+\.\d+`)
   - Any branch with a commit dated within the last 90 days (`git log -1 --format=%ct origin/<name>`, compared against now minus 90 days)
2. **Merge check — ancestry only:** a branch is a candidate only if
   `git merge-base --is-ancestor origin/<name> origin/$DEFAULT` exits 0.
   - Do **not** substitute name heuristics, PR "merged" badges, or squash-merge detection. A squash-merged branch will fail this check and be kept — that is the correct, safe outcome. A branch holding an unmerged release fix will also fail this check and be kept. False negatives (keeping deletable branches) are acceptable; false positives are not.
3. For each candidate, record: branch name, tip SHA, last commit date, last author.

Write the full candidate list to `branch-deletion-candidates.txt` in the repo's parent directory (not inside the repo — do not create commits or dirty the working tree).

**Sanity gates — abort branch deletion entirely (still produce the report) if any of these trip:**
- Any excluded/protected name appears in the candidate list.
- The candidate list contains more than 80% of all remote branches.
- The candidate list is empty but the repo has 400+ branches *and* `git fetch` failed or was skipped (indicates stale data).

## Phase 2 — Backup, then delete branches

1. **Backup first, unconditionally:** create `git bundle create ../stale-branch-backup-$(date +%Y%m%d).bundle` covering every candidate tip SHA, and append every `<branch-name> <tip-SHA>` pair to the log file. Verify the bundle with `git bundle verify` before proceeding. Any branch can then be restored later with `git push origin <SHA>:refs/heads/<name>`. If the bundle cannot be created or verified, abort deletion.
2. Delete in batches of 20 via `git push origin --delete <names...>`, pausing briefly between batches.
3. After each batch, confirm the deletions took effect (`git ls-remote` on a sample) and append the deleted names + SHAs to the log.
4. If any deletion returns an error (protected branch, permission denied, non-fast-forward), skip that branch, log the error, and continue. **Never** retry with force flags, never touch tags, never force-push anything, never delete local branches on this machine beyond normal prune.

## Phase 3 — CI artifacts (GitHub Actions)

1. List artifacts with `gh api /repos/{owner}/{repo}/actions/artifacts --paginate`.
2. A candidate for deletion is an artifact whose `created_at` is more than 30 days ago. Exclude artifacts belonging to workflow runs triggered by tags or releases (check the run's `event` and `head_branch`) — release build outputs may be the only remaining copy.
3. Log each candidate (id, name, size, created_at, associated run) before deleting, then delete via `gh api -X DELETE /repos/{owner}/{repo}/actions/artifacts/{id}`.
4. Delete **artifacts only**. Do not touch caches, packages, releases, release assets, or workflow run history.
5. Respect rate limits: if the API returns 403/429, back off and resume; if it persists, stop and report partial progress.

## Hard rules (apply to the whole task)

- No deletion without a prior logged backup path or logged metadata sufficient for recovery.
- Never delete based on age alone, name alone, or any heuristic other than the exact criteria above.
- Never modify branch protection rules, repo settings, or CI configuration.
- On any unexpected state (detached weirdness, remote mismatch, auth prompt, >5 consecutive errors), stop destructive work immediately and write the report with what was done so far.
- Do not commit, push commits, or open PRs. This task only deletes refs and artifacts.

## Final report

Produce a plain-text report containing:
- Remote URL and default branch used.
- Branches: total counted, excluded (with reason categories), candidates, deleted, skipped-with-error. Path to the backup bundle and the candidate/deletion log.
- Artifacts: total counted, candidates, deleted, skipped, approximate storage reclaimed.
- Exact recovery instructions (bundle path + `git push origin <SHA>:refs/heads/<name>` recipe).
- Any aborted phases and why.
