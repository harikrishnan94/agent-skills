# reduce-complexity evals — iteration 1 notes

Layout mirrors `evals/humanize/`: `evals.json` manifest, `files/<fixture>/setup_fixture.sh`
building main + a multi-commit feature branch (branch archaeology is a graded feature),
deterministic graders under `graders/`. Unlike humanize, graders score the **report text**
(`report.md` at the repo root) and additionally assert the repo is untouched — the skill is
report-only. Run a grader as `python3 graders/check_<name>.py <fixture-repo>`.

## Live-run results (one run per configuration, executor = fable, 2026-07-13)

| Fixture | with skill | without skill (baseline) |
| --- | --- | --- |
| seeded-accretion-logship | 5/5 | 5/5 |
| inherent-only-paygate | 6/6 | 5/6 (fails `tests_not_deduplicated`) |
| mixed-stockroom | 6/6 | 5/6 (fails `flags_within_diff_duplication`) |

## Which assertions discriminate (the humanize-benchmark caveat applies)

At this model tier the baseline finds all three logship plants, so the must-find
assertions there measure the model, not the skill. Observed discriminators:

- `tests_not_deduplicated` (paygate): the baseline recommended merging the webhook-level
  dead-letter test into the retry-level one; the skill's never-flag list (deliberate test
  duplication) suppresses this. Added after the first run pair, then validated against
  both stored reports.
- `flags_within_diff_duplication` (stockroom): the baseline missed tying `export_csv`/
  `export_json` to the duplicated normalization block; the skill's shape catalog names it.
- Report *shape* differences that current assertions don't score: the skill run produced
  3 findings vs the baseline's 5 on logship (proportionality), and 0 removable findings +
  1 question vs 4 findings on paygate.

## Fixes made during iteration 1

- paygate fixture originally left `next_delay`/`to_row`/`from_row` with only test
  consumers — an accidental *real* accretion inside the false-positive fixture. Both runs
  correctly noticed it. Fixed by wiring them into `webhook.process_event` (retry
  scheduling + state round-trip via `charge.retry` events).
- That fix itself planted flaggables, caught over two more live rounds: a no-op
  `tuple()` around `from_row`'s argument (the with-skill run's *only* finding in round
  2 — precise), the dead-letter threshold living in `retry_charge` while REVIEW.md says
  transitions belong on the dataclass, `next_delay` taking a whole state for one int,
  and finally the `state=None` parameter threading across `handle`/`process_event`
  (round 3's with-skill finding: "adapter between two halves of the same change" —
  correct per the catalog). Fixed by `record_failure()` owning increment + dead-letter,
  `next_delay(attempts)`, and deriving state inside `process_event` from the event
  payload. Lesson for fixture authors: run the false-positive fixture live after ANY
  edit — a well-calibrated reviewer finds whatever wart you just introduced, so the
  fixture converges only when the runs come back empty.
- `question_blocks` in `common.py` originally counted narrative mentions ("one item
  survives — a question for the author") as question items; now only disposition-marked
  or explicitly labeled question items count.

## Ideas for iteration 2

- Sharpen logship: add a proportionality assertion (e.g. no removal verdict on the
  branch's core feature surface — `export_batches` itself) so the must-find fixture also
  measures restraint; baseline run 1 proposed dissolving `Batch`/`BatchWriter` wholesale.
- More runs per configuration before trusting any single assertion delta (n=1 here).
- Consider grading the report's structure (severity × disposition present, evidence
  categories named) — the skill's format survived verbatim in with-skill runs.

## Iteration 2 (2026-07-14): second literature survey + rewrite

SKILL.md rewritten from an 8-facet survey (foundations, refactoring canon, review-practice
research, production AI-review tools, LLM failure modes, mechanical-evidence standards,
skill authoring, accretion phenomenon) + 3-lens critique (precision / coverage / operator).
Headline changes: production-dead-test-alive disposition (fixes the "(grep, tests included)"
contradiction the paygate history proved wrong), a 6-step liveness protocol with
evidence-kind-picks-the-verb, new-external-evidence-only refutation + kill questions +
auto-drop classes in Step 6, six-finding cap with inverse diff-size scaling, dropped-
candidates appendix + clean-report variant, flag-lifecycle pass (kill-switch exemption,
residue halo, test-choice), five new catalog rows, a rejected-candidate worked example,
and a rationalization table. Rejected: numeric confidence gates (same-context self-scores
are noise), references/ split (owner rule), consensus verification.

### Live-run results (executor = fable, 2026-07-14)

| Fixture | with rewritten skill |
| --- | --- |
| seeded-accretion-logship | 5/5, 5/5 |
| inherent-only-paygate (repaired fixture) | 6/6, 6/6, 6/6 — 0 findings each |
| mixed-stockroom | 6/6, 6/6 |

### Grader fixes (regex artifacts surfaced by the richer report format)

The new report format (scope preamble, coverage summary, dropped-candidates appendix)
tripped block-heuristic regexes on narrative text, all fixed in graders/:
- `REMOVE_RE`: "dead" no longer matches "dead-letter" / "dead letter".
- `KEEP_RE`: added require\w*, accepted, killed, suppress\w* (dropped-candidate and
  scope-preamble vocabulary).
- `tests_not_deduplicated`: the dedup verb must be within ~6 words of "test" — a test
  file cited as *evidence* in a non-test finding no longer counts.
- `preexisting_bucketed`: only blocks that *act on* legacy_price_rules (REMOVE_RE or
  UNIFY_RE) violate the bucket rule; evidence-of-absence mentions don't.

### Paygate fixture repair (round 4)

All three first-round runs independently surfaced the same real wart left by the round-3
repair: the wire format encoded fresh-vs-resume twice (event type AND `"state" in event`
— only the latter read) and the event id twice (`event["id"]` AND `row[0]` — resume path
ignored `event["id"]`; test_dead_letter_after_max_attempts even relied on created+state).
Fixed by making the event type the single discriminator (`event["type"] ==
"charge.retry"` → `from_row(event["id"], event["state"])`) and shrinking the row to
`(attempts, status)`. Reconvergence: 3/3 fresh runs returned 0 findings (1, 1, 0 open
questions — each a legitimately ambiguous cross-repo contract question). The lesson from
iteration 1 held exactly: the false-positive fixture converges only when live runs come
back empty.

### Ideas for iteration 3

- The planned logship proportionality assertion (no removal verdict on `export_batches`)
  is still unimplemented; the rewrite added the core-surface guard text it would measure.
- Grade dropped-candidates quality: every suppressed candidate should name the evidence
  that killed it (one-line-each format is in the skill now).
- Baseline (no-skill) comparison runs were not repeated this iteration; rerun both arms
  ≥3x before attributing any assertion delta to the rewrite.

## Iteration 3 (2026-07-14): apply-by-default

SKILL.md flipped from report-only to fix-by-default (owner request), then hardened by a
3-lens adversarial review + verification pass. Final contract: imperative invocation →
apply findings that clear Step 7's gate (per-fix-type oracle: restructures need
remove-verdict evidence + tests; production-dead deletions take liveness receipts as
coverage; text-only edits need only post-apply verification), one finding at a time
against a preflight baseline, revert = inverse-apply own recorded edits, everything
uncommitted; question-phrased or "just report" invocation → read-only run.

### Harness changes

- Evals 1–3 kept verbatim: their prompts all carry explicit report-only language, so they
  now test the read-only path (the `repo_untouched_report_only` assertion is doing real
  work again — it verifies the mode gate, not a tautology).
- NEW eval 4 `apply-default-logship` (imperative prompt, `graders/check_apply.py`):
  HEAD still at fixture-head with uncommitted code edits, legacy flag gone from the tree,
  `_chunk` deleted, `unittest discover` green afterward, report carries `Status: applied`
  + a verification receipt, adapter at least addressed, touched paths ⊆ allowed set.
- NEW eval 5 `question-mode-logship` (question prompt, reuses `check_seeded.py`): the
  question-phrased gate must hold — tree untouched, findings still reported.

### Live-run results (executor = fable, 2026-07-14, one round)

| Eval | Result |
| --- | --- |
| 1 seeded-accretion-logship (report-only) | 5/5 |
| 2 inherent-only-paygate (report-only) | 6/6 after grader fixes; fresh confirm run 6/6 (0 findings, 1 question, 7 dropped) |
| 3 mixed-stockroom (report-only) | 6/6 |
| 4 apply-default-logship | 7/7, 7/7 (two runs; both fixed flag + `_chunk` in-tree, uncommitted, suite green) |
| 5 question-mode-logship | 5/5 (tree untouched) |

### Grader artifact fixes (round 1 of this iteration)

All three first-pass e2 failures were block-heuristic artifacts on a model 0-finding
report — the block-first rule held again:

- `blocks()` now merges a heading-only chunk into the following one: the skill's
  clean-report narrative puts "### Strongest candidate: …" in its own block, and the
  paragraph under it (naming `verify_signature` + "redundant") read as a removal
  recommendation without its heading/verdict context.
- `KEEP_RE` += `candidates?`: candidate-description blocks are suspicions, not verdicts.
  Known trade-off: a real removal finding worded as a "candidate" would now
  false-negative; the skill's format titles real findings imperatively, so accepted.
- `REMOVE_RE`: `dead(?![ -](letter|guard|state))` — the paygate DEAD retry state gives
  reports "dead guard"/"dead state" phrases that are domain nouns, not removal claims.
- `check_inherent.py` dedup verb: `merg(?!e[- ]base)` — every report's Scope section is
  required to state the merge-base.

### Observation for iteration 4

Both apply runs also unified the `Batch`/`BatchWriter` adapter — inlining and deleting
`batch.py` + `writer.py` (suite green, done as sequential single mechanical fixes). That
skirts Step 7's "compound multi-file restructures are report-only" line; the graders are
deliberately neutral (`adapter_addressed` accepts applied or report-only). Iteration 4
should either sharpen "compound" in the skill (files touched? behavior surfaces crossed?)
or add an assertion taking a side.

### Ideas for iteration 4

- Still unimplemented: the logship proportionality assertion (no removal verdict on
  `export_batches`).
- An apply-mode false-positive eval: an imperative invocation on paygate must apply
  NOTHING (everything is inherent) — apply-mode restraint is currently untested.
- A dirty-tree apply eval: uncommitted user edits in a fixture file → the skill must
  demote findings touching it, never `git restore`, and the user hunks must survive.
- More rounds: this iteration is n=1 for evals 1/3/5, n=2 for evals 2/4; rerun before
  trusting any assertion delta. Baseline (no-skill) arm still unrun for iteration 3.
