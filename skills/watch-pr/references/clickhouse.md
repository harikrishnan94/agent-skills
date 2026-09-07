# ClickHouse CI rounds

Run from the correct PR worktree. Start with the robot's CI-report comment and
the underlying Praktika reports; GitHub Actions logs often contain less detail.

```bash
node .claude/tools/fetch_ci_report.js "$PR_URL" --all --links
node .claude/tools/fetch_ci_report.js "$PR_URL" --failed --cidb
python3 .claude/tools/fetch_perf_report.py "$PR_URL" --json
```

Check that the report SHA and workflow match the observed revision. Inspect
Cloud performance bot comments too; their verdict may not appear as a failing check.
Follow the links actually returned by the bot and reports. If a parser fails,
retain the error and inspect the underlying JSON. Never invent an S3 path or
interpret an empty parser result as a clean run.

For `CH Inc sync`, distinguish conflicts, build failures, and test failures.
Do not classify the whole check as infrastructure. A private-side failure still
needs evidence and may require a separately authorized private-repository change.
The existing `fix-sync` skill can supply diagnosis when available; its mutation
steps remain subject to the user's current scope.

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
