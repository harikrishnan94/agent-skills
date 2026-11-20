# Task: Diagnose and fix the search API p95 latency regression (suspect: query-result cache)

You are an autonomous agent running unattended overnight. No human is available to answer questions. Make decisions yourself, document your reasoning, and leave the repository in a safe, reviewable state. Everything you need to know is in this prompt.

## Background

- The search API's p95 latency has regressed roughly **30% over the last month**.
- The prime suspect is the **query-result cache** in `searchd/cache.py`, but the suspicion is unconfirmed — verify before you optimize. The real cause may be elsewhere in the repo.
- The regression accumulated over ~1 month of commits, so it may be one bad commit or several small ones.

## Hard constraints

1. **The public API must not change.** No changes to public function/method/class signatures, module-level names other code imports, HTTP endpoints, request/response shapes, or documented configuration semantics. Internal refactors are fine. If the only fix you can find requires an API change, do NOT make it — document it as a recommendation instead (see "If you cannot fix it" below).
2. **Correctness over speed.** A cache that returns stale or wrong results is worse than a slow one. Any behavior change to caching (eviction, TTL, key computation, invalidation) must preserve result correctness. Run the project's test suite (look for `make test`, `pytest`, `tox`, or a CI config to find the right command) after every change and before declaring success.
3. **Do not push to any remote. Do not force-push, rebase shared branches, or delete anything.** All work happens on a local branch (see "Deliverables").
4. Do not edit the benchmark or load-test harnesses to make numbers look better. If a harness is broken, fix it minimally, document the fix, and re-establish the baseline from scratch.

## Tools available

- `make bench` — runs the benchmark suite; writes results to `bench/results.json`. Inspect that file's schema on your first run to learn which fields hold latency percentiles (look for p95 or equivalent).
- `scripts/loadtest.sh` — a load-test rig for closer-to-production validation. Read the script first to learn its usage, flags, duration, and where it writes output.
- Full git history of the repository.
- Standard tooling: Python profilers (`cProfile`, or whatever the repo already uses), the test suite, editors.

## Critical: benchmark noise protocol

Bench numbers vary **±10% between identical runs**. A single run proves nothing. Follow this protocol for every measurement you rely on:

- **A "measurement" = at least 5 consecutive `make bench` runs** of the same code. Record the p95 from each run's `bench/results.json` (copy each results.json aside before the next run overwrites it, e.g. to `bench/archive/<label>-runN.json`).
- Compare configurations using the **median of the 5+ p95 values**. Also record min and max so the spread is visible.
- **Decision rule:** treat configuration A as faster than B only if the median improvement exceeds ~10–15% or the two sets of runs do not overlap. A 5% median delta with overlapping ranges is noise — say so, don't claim it.
- Since the target regression is ~30%, a genuine fix should show a clearly separated, large improvement. If your fix shows only a marginal, overlapping improvement, the real cause is likely still unfound — keep investigating.
- Keep the machine load consistent: don't run other heavy processes concurrently with benchmarking, and never run `make bench` and `scripts/loadtest.sh` simultaneously.

## Plan of work

Work in this order. Timebox yourself loosely: if any phase stalls for more than ~1–2 hours of effort with no progress, write down what you tried and move to the fallback path.

### Phase 0 — Setup and baseline
1. Create and switch to a local branch: `git switch -c fix/search-p95-regression` (branch from the current main/default branch head).
2. Confirm `make bench` works end to end; inspect `bench/results.json` to identify the p95 field(s).
3. Establish a **current-code baseline measurement** (5+ runs per the noise protocol). Save the numbers.
4. Run the test suite once to confirm it passes on unmodified code, so you can distinguish pre-existing failures from ones you introduce.

### Phase 1 — Find the regression
1. Review git history for the last ~5–6 weeks, starting with `git log --follow -p -- searchd/cache.py`, then broadening to the rest of `searchd/` and anything the hot path imports (also check dependency pins: lockfiles, requirements changes).
2. Pick a commit from before the regression window (~5–6 weeks ago) and measure it (worktree or checkout, 5+ bench runs). If old-code p95 is clearly better per the decision rule, you've confirmed the regression is reproducible in the bench harness. If the bench shows **no** difference between old and new code, the bench may not exercise the regressed path — note this, and lean on `scripts/loadtest.sh` for measurement instead, applying the same 5-runs-and-median discipline to whatever latency numbers it reports.
3. Locate the offending change. Prefer targeted checking of the handful of suspicious commits (cache-related first) over a full bisect; use `git bisect` with a bench-based check only if inspection fails — remember each bisect step costs 5+ bench runs, so shrink the suspect range by inspection first.
4. Independently of history, **profile the current hot path** (cProfile or sampling profiler around the benchmark workload). Look for classic cache pathologies: lowered hit rate (key includes something newly non-deterministic like a timestamp or unsorted dict/set ordering), oversized serialization/deserialization on get/put, lock contention, O(n) scans on eviction, accidental cache bypass, TTL set too low, cache size shrunk.
5. Write down the identified root cause with evidence (commit hash(es), profile output, hit-rate numbers if obtainable) before changing anything.

### Phase 2 — Fix
1. Implement the smallest change that addresses the root cause. If the cause is a specific commit, prefer a targeted fix or revert of the regressed logic over a wholesale `git revert` if other functionality landed in the same commit — but a clean revert is acceptable when it's safe and API-compatible.
2. Keep commits small and well-explained: what regressed, why, how the fix works, and the before/after numbers.
3. Re-run the full test suite. All previously-passing tests must still pass.
4. If the root cause turns out to be outside `searchd/cache.py`, fix it there instead — the goal is the p95 regression, not the cache per se. The same constraints apply.

### Phase 3 — Verify
1. Take a **post-fix measurement** (5+ bench runs) and compare to the Phase 0 baseline using the decision rule. Target: recover most of the ~30% regression, i.e. a clear, non-overlapping improvement.
2. Run `scripts/loadtest.sh` against the fixed code (and, if time permits, against unfixed code for comparison) to confirm the improvement holds under realistic load and that error rates/throughput did not degrade.
3. Re-verify the public API is unchanged: diff the public surface (exported names, signatures, endpoint routes) between your branch and the base branch.
4. Run the test suite one final time on the exact commit you're leaving as the result.

## If you cannot fix it (fallback path)

Do not thrash. If, after genuine effort, you cannot identify the root cause, cannot fix it within the constraints, or cannot demonstrate an improvement that clears the noise threshold:

- Leave the branch with **no speculative half-fixes** — revert anything you can't justify with measurements.
- Still deliver the report (below) containing: everything you ruled out with evidence, the most promising remaining hypotheses ranked, exact measurements taken, and concrete recommended next steps (including any fix that would work but requires an API change).
- A rigorous negative result with a narrowed suspect list is a successful outcome for this run. A "fix" backed by one noisy bench run is not.

## Deliverables

All work on local branch `fix/search-p95-regression`, committed (not pushed). Leave the working tree clean.

1. **The fix** (if achieved) as one or more focused commits.
2. **A report at `bench/REGRESSION-REPORT.md`** (committed to the branch) containing:
   - Root cause: what regressed, in which commit(s), and why it hurt p95 (or the fallback analysis above).
   - The fix and why it's API-compatible and correct.
   - Measurement table: baseline vs. fixed — all individual p95 values per run, medians, and spread, for both `make bench` and the load test. State explicitly that the improvement clears the ±10% noise band, with the numbers that show it.
   - Test suite status before and after.
   - Anything a human reviewer should double-check.
3. **Archived raw bench outputs** under `bench/archive/` (the per-run results.json copies), committed or at minimum left in the working tree per the repo's gitignore rules.

## Success criteria (all must hold)

- Root cause identified with evidence, or fallback report explains why not.
- If fixed: median p95 across 5+ post-fix bench runs improves on the baseline by more than the noise band, and the load test corroborates it.
- Public API byte-for-byte compatible; full test suite passes.
- Nothing pushed to remotes; all work reviewable on the local branch with the report.
