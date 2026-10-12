# Evidence checks

These are Hari's recurring checks. The repository's review skill covers the
general gates (contract, impacted surface, failure paths, changelog rules);
do not repeat them here.

## Performance

- **Is the problem still there on the current base branch?** Another change
  may already have fixed it.
- **Does each benchmark reach the changed code?** Classify each query: it
  hits the changed path, uses it only during setup, consumes its output, or
  never reaches it. A timing difference alone does not prove the cause. If a
  benchmark misses a regime, say what it does not cover, not that it is
  wrong.
- **Is the comparison right?** It should be base vs PR, not feature on vs off
  inside the PR build. Baselines must be comparable.
- **Does it cover every regime the new path accepts?** That means every type,
  size and shape, and both sides of each threshold. Typical gaps: only small
  strings, only sequential probes, only small build sides, or a type that
  gains nothing but now takes the new path.
- **Are the settings realistic?** Use the algorithm and thread count users
  actually get.
- **What to ask for:** before/after on a grid of sizes plus the default, in
  absolute time, using the issue's repro, and a performance test so it does
  not regress.
- **Parity claims:** `p > 0.05` alone is not parity. Ask for confidence
  intervals or an equivalence margin, and the raw samples.
- **Regressions:** small ones are fine if the description documents them
  with numbers. Unproven claims come out of the changelog.
- **Thresholds:** ask for a crossover measured over a range, a named
  constant, and a comment saying how it was chosen. If a cutoff stands in
  for a cost trade-off, propose a rough break-even formula, and ask for
  experiments that measure each side. Example:
  `gathered_rows * saved_per_row > build_rows * construction_per_row`.
- **Experiments**, only after asking Hari: one binary, with the arms
  switched by a runtime setting. On every run, check that each arm used only
  its own mechanism (profile events, identical result checksums).

## Correctness

- State the real invariant, not the symptom. For example: "equal keys from
  both sides land in the same bucket", not "a row hashes the same before and
  after spill".
- If code becomes unreachable, ask to replace it with an assertion rather
  than delete it silently.
- Argue bot blockers on the mechanism, and hedge: "I think it is not a
  regression: ...".

## Tests

- The test must prove the behavior, not a proxy. Output sent to `FORMAT
  Null` plus a counter misses wrong results. A count of created files does
  not prove any bytes were spilled.
- The test must reach the path. A minimum set above the whole input never
  triggers it.
- If an old test still asserts the previous behavior, point at the exact
  assertion and at the nearby comments that are now stale.
- Ask for variants of what the change touches: other join algorithms,
  nullable keys, the setting's default.

## Description

- It must match the code: defaults, scope, which types benefit.
- A sentence that needs two reads should be split.
- The changelog entry gets concrete numbers, no "Closes #", and no
  authoring log.

## Design and scope

- **Default-on bar:** on by default, with a clear threshold where the gain
  is meaningful and nothing regresses. If it is off by default, nobody runs
  it.
- Prefer decisions made at runtime, from real counts, over plan-time
  estimates that cannot see skew.
- Put one rule in one place. If the PR adds a second implementation of a
  mechanism that already exists, that is a finding, not a design preference:
  ask for one path in this PR. A lambda copied to several call sites becomes
  a helper. Reuse existing constants.
- If the PR is part of a larger change, the rest belongs in a separate PR.
