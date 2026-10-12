# ClickHouse specifics

## Sources

- **Review gates:** `.claude/skills/review/SKILL.md`. **Changelog rules:**
  the `clickhouse-pr-description` skill.
- **CI report:** `.claude/tools/fetch_ci_report.js`, or the report links in
  the CI status comment. Expired reports return 403. Then use the public CI
  database on play.clickhouse.com:
  - `default.checks` holds test results and history, which tells a failure
    the PR causes from a flaky one.
  - `default.query_metrics_v2` holds per-query performance comparisons for
    PRs and master. Its columns include `pr_number`, `old_sha`, `new_sha`,
    `test`, `query_index`, `metric`, `old_value`, `new_value`, `diff`,
    `stat_threshold` and `arch`.
  - Treat a `diff` below `stat_threshold` as noise.
  - Check which base commit a report compared against.
- **CH Inc sync:** while this check is pending or failing, the PR cannot
  merge, even if the code is approvable.

## Authors

- `groeneai` is an AI agent account and takes instructions in comments: "make
  it merge ready", "fix the CI issues".
- `clickgapai` opens coverage-gap test PRs.
- Most human authors are experienced contributors.

## Hari's recurring asks

- **Joins:** benchmark with the algorithm users get (`parallel_hash` for
  parallel claims, not `hash` alone). Check `hash`, `parallel_hash` and
  `grace_hash` when shared join code changes.
- **Constants:** reuse existing ones, such as `DB::CH_CACHE_LINE_SIZE` from
  `Common/CacheLine.h`.
- **Unreachable code:** `chassert(...)`, not silent deletion.
- **Performance tests:** a performance improvement needs a test under
  `tests/performance/`.
