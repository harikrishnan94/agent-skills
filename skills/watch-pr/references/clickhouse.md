# ClickHouse CI rounds

Run from the correct PR worktree. Start with the robot's CI-report comment and
the underlying Praktika reports; GitHub Actions logs often contain less detail.

```bash
node .claude/tools/fetch_ci_report.js "$PR_URL" --all --links > "$STATE_DIR/ci-inventory.log"
node .claude/tools/fetch_ci_report.js "$PR_URL" --failed --cidb > "$STATE_DIR/ci-failures.log"
python3 .claude/tools/fetch_perf_report.py "$PR_URL" --json > "$STATE_DIR/performance.json"
```

Check that the report SHA and workflow match the observed revision. Inspect
Cloud performance bot comments too; their verdict may not appear as a failing check.
Follow the links actually returned by the bot and reports. If a parser fails,
retain the error and inspect the underlying JSON. Never invent an S3 path or
interpret an empty parser result as a clean run.

Fetch the full report inventory once per revision; thereafter inspect changed or
failed jobs and linked artifacts. Keep verbose reports in files. Cache evidence
by tested revision, configuration, job, attempt, and signature; invalidate only
what changed. Cloud/performance reports still need refresh while pending.

## CH Inc sync

Treat public and private PRs as one investigation with separate worktrees and
authorization. Read the public head's latest `CH Inc sync` status description and
target URL. Resolve the private PR from that evidence; the usual branch is
`sync-upstream/pr/<public-number>` in `ClickHouse/clickhouse-private`. Verify its
actual repository/branch instead of assuming `origin`. Read-only discovery:

```bash
gh pr list --repo ClickHouse/clickhouse-private --head "sync-upstream/pr/$PR_NUMBER" --state all --json number,url,state,headRefName,headRefOid,baseRefName
```

Record public head, private PR/head/base, the public revision the sync producer
incorporated, and private CI attempts/report SHAs. A branch name or green private
run alone does not prove it tested the current public revision. Verify lineage
or producer metadata; unknown mapping remains `UNSETTLED`.

- **Conflicts:** apply the main skill's semantic merge procedure in an isolated
  private worktree. Preserve both public intent and private-only behavior/configuration;
  never default to upstream hunks. Review interacting clean merges too.
- **Build/test failures:** inspect actual private reports and reproduce the failing
  configuration. Adapt private consumers when that preserves the intended public
  API; do not revert the public benefit just to satisfy private code.
- **Missing sync, stuck testing, stale status:** distinguish creation/refresh failure,
  access denial, queued jobs, and status propagation. Inspect producer state and
  last progress. Use an authorized recovery or name the external dependency.
- **Flaky/infra:** require the same attribution evidence as public CI. Timeouts,
  server startup errors, and files outside the diff can still be PR regressions.
  Justified reruns need terminal verification; triggering one is not completion.

The repository's `fix-sync` skill may supply diagnostic commands. Its shortcuts
do not override this watcher's intent, attribution, validation, ownership, or
completion gates. Builds are not optional evidence merely because that skill
offers to skip them. If local verification is unavailable, require matching CI.

Before a private push, fetch and reconcile concurrent sync-bot changes using the
main skill's ancestry gate. After any public update, recheck the mapping and
private attempts. Verify private mergeability and applicable CI, then confirm the
current public head's `CH Inc sync` status reflects that result. Do not stop at
"mergeable", "rerun started", or "should pass shortly". Inaccessible evidence
is a named blocker. Keep private log details out of public posts.

## Attribution and validation

For failure attribution, compare the exact signature against `master` history
and source. Use reproductions or discriminating probes when history is ambiguous.
A nonzero master flake rate does not prove the PR has not introduced a deterministic bug.

For performance changes, inspect which changed paths the query actually executes.
Use the repository's performance tools and methodology; timings alone do not
establish causality. Report unverified performance explanations as `UNSETTLED`.

Follow the worktree's `AGENTS.md` for builds, tests, style, and PR text. In particular:

- Redirect builds/tests to unique logs in the build directory and have a subagent
  summarize them. Let `ninja` choose parallelism. Build the targets the fix needs;
  building `clickhouse` does not build `unit_tests_dbms`.
- Match the failing configuration. Release builds cannot verify debug-only assertions.
- Use the repository's test-server setup. Missing cluster services, logging, or
  fixture paths can manufacture local failures unrelated to either revision.
- Run the local style check before pushing. Use `.github/PULL_REQUEST_TEMPLATE.md`
  for any authorized PR-body update, with the mandatory `🕵️ ` prefix.
- Use new commits, and preserve the PR's target branch. Do not create stacked PRs
  or broaden this watcher into fixes for unrelated failures.
