# Task: Eliminate the intermittent pip resolver timeout in the `wheel-build` GitHub Actions job

## Background

This repository has a GitHub Actions job named `wheel-build` that fails roughly once a week with a pip resolver timeout. Re-running the failed job always succeeds, so the failure is intermittent (network flakiness or dependency-resolution backtracking), not a deterministic break. Your job is to find the root cause and fix the workflow so these failures stop happening — not to paper over them by re-running jobs.

The repository owner (Hari) is available at his desk. If you hit a hard blocker — missing `gh` authentication, the job lives in a different repository, or a decision below is ambiguous in a way you cannot resolve from evidence — pause and ask him rather than guessing.

## Step 1: Locate the job

1. Search `.github/workflows/*.yml` (and `.yaml`) in this repository for a job with id or `name:` of `wheel-build`.
2. If it is not in this repository, ask Hari which repository it lives in before proceeding.
3. Read the full workflow: note every `pip install` / `pip wheel` / `python -m build` invocation, the runner OS matrix, Python version matrix, and whether any pip caching (`actions/setup-python` with `cache: pip`, or `actions/cache`) is configured.

## Step 2: Gather failure evidence (do this before changing anything)

Use the `gh` CLI (read-only operations):

1. `gh run list --workflow <workflow-file> --status failure --limit 30` to find recent failures.
2. For at least the 3 most recent failures, download logs with `gh run view <run-id> --log-failed` (or `gh api` if needed).
3. From the logs, pin down for each failure:
   - The exact command that failed and the exact error text.
   - Which failure mode it is:
     - **Network timeout**: errors like `ReadTimeoutError`, `Connection to pypi.org timed out`, HTTP 5xx from PyPI or a mirror.
     - **Resolver backtracking**: long stretches of `INFO: pip is looking at multiple versions of <pkg>` / "This is taking longer than usual" before the job's timeout kills it, typically caused by unpinned or loosely-pinned dependencies.
   - Whether failures cluster on one OS/Python matrix entry or one package.

If `gh` is not authenticated or you cannot access the runs, ask Hari to run `gh auth login` or to paste a failing run's log.

## Step 3: Fix the root cause

Choose the fix that matches the evidence. Preferred fixes, in order:

1. **If resolver backtracking**: eliminate the resolution work at CI time.
   - Pin the build/install dependencies with a constraints or lock file (e.g., `pip-compile` output committed to the repo, passed via `pip install -c constraints.txt`), or tighten the offending version specifiers.
   - Where wheels are being built for distribution, do not change the package's own declared dependency ranges in `pyproject.toml`/`setup.cfg` unless the logs prove a specific specifier is the cause — constrain the CI environment instead.
2. **If network flakiness**: make pip resilient and reduce network dependence.
   - Add `PIP_RETRIES=10` and a reasonable `PIP_TIMEOUT` (e.g., 60) via env vars or flags on the failing invocation.
   - Enable pip caching in the workflow if absent (`actions/setup-python` `cache: pip` keyed on the lock/requirements file).
3. **Only as a last resort**, and only in addition to (not instead of) the above: wrap the single flaky step in a bounded retry (e.g., 2–3 attempts of just the pip step, not the whole job). Do not add a whole-job rerun mechanism.

Constraints:

- Keep the diff minimal and confined to what the evidence justifies. Do not upgrade dependencies, change what artifacts get built, restructure the workflow, or touch unrelated jobs.
- Do not disable or weaken the job (no `continue-on-error`, no removing matrix entries).
- Match the repository's existing workflow style and pinning conventions.

## Step 4: Verify

1. Lint the modified workflow (`actionlint` if available, otherwise careful YAML review).
2. Reproduce the install/build path locally or in a container where feasible: run the same pip command(s) with your changes (fresh venv, same Python version as one matrix entry) and confirm resolution completes quickly and deterministically.
3. Push your changes to a new branch and confirm the `wheel-build` job passes on that branch (via the PR's checks or `workflow_dispatch` if the workflow supports it). A weekly flake cannot be re-triggered on demand — passing runs plus evidence-backed reasoning is the bar, and your PR description must explain why the specific failure mode you found can no longer occur.

## Deliverable

- A branch (named e.g. `fix/wheel-build-pip-timeout`) and an open pull request against the default branch. Do not merge it and do not push to the default branch directly.
- The PR description must include: the failure mode identified (with quoted log excerpts and run IDs as evidence), the fix and why it addresses that mode, and what was verified.
- If, after examining the logs, the failures turn out not to be fixable in-repo (e.g., a corporate proxy or self-hosted runner network issue), do not guess: write up the evidence and ask Hari how to proceed.

## Success criteria

- Root cause identified from actual failure logs, not assumed.
- Workflow change is minimal, targeted, and does not mask failures.
- `wheel-build` passes on the PR branch.
- PR is open with the evidence-backed explanation described above.
