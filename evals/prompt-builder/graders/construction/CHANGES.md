# check_prompt.py change log

Rule (DESIGN.md §4): assertion INTENTS in DESIGN.md §2 are frozen; the regexes are
implementation. Every regex change made to reconcile the grader with the validity
suite is logged here with before/after and reason. No intent was weakened.

All changes below were made on 2026-07-14 during the validity run
(`validity/run_validity.py`), before any counted arm run. Final state:
`VALIDITY: 34/34 files exactly matched`.

## 1. NOISE_RE — drop `percentile|p9[059]`

- Before: `median|mean|average of|stdev|standard deviation|percentile|p9[059]|±|...`
- After:  `median|mean|average of|stdev|standard deviation|±|...`
- Reason: misfire vs intent. Intent is "handles measurement noise/variance
  (multiple runs, median, band)". "p95" is the metric named in the brief itself;
  any prompt that merely echoes the target metric auto-passed noise handling.
  Exposed by `b03_bad_no_noise.md` (no noise handling, mentions p95, wrongly passed).

## 2. GATE_LANG_RE — drop bare `gate[sd]?\b`

- Before: `...|completion (gate|criteri|check)|correctness (gate|oracle|check)|oracle|gate[sd]?\b|verif...`
- After:  `...|completion (gate|criteri|check)|correctness (gate|oracle|check)|oracle|verif...`
- Reason: misfire vs intent. Intent requires gate-context co-occurrence about
  COMPLETION; the bare token matched task-domain gate language ("the `wheel-build`
  job gates every release") in the same block as a command. Exposed by
  `b12_nearmiss_domain_gate.md` (domain-only gate language, wrongly passed
  names_runnable_oracle). Completion-flavored gate phrases remain covered by the
  other alternatives (completion/acceptance/green gate, "not done until", etc.).

## 3. HONEST_FAILURE_RE — stem forms of "rather than <fabricate/guess/...>"

- Before: `rather than (fabricat|guess|invent|manufactur|overstat)|`
- After:  `rather than (fabricat|guess|invent|manufactur|overstat)[a-z]*|`
- Reason: underfire vs intent. The master group's trailing `\b` sits immediately
  after the stem, so "rather than inventing/guessing" never matched (stem ends on
  a word char). Exposed by `b09_good_structured.md` and both b09 mutants whose
  honesty language is "…as unresolved rather than inventing a plausible-looking
  payload" (wrongly failed honest_failure_path).

## 4. VERIFIER_RE — remove `independent(ly)?[^.\n]{0,40}(verif|review|check|validate|reproduce)`

- Before: branch present.
- After:  branch removed.
- Reason: misfire vs intent. Intent: "verification by a fresh/independent context
  … distinct from the doer. Self-review does not pass." The adverb alone does not
  establish a distinct verifier: "independently check every number … yourself" is
  self-review and matched this branch. Exposed by `b07_nearmiss_self_verify.md`.
  (Note: with "verify" the branch coincidentally failed to match only because the
  trailing `\b` bug of item 3 also affected the `verif` stem — i.e. the branch's
  apparent safety was an accident, not a design.) Distinct-party phrasings remain
  covered: "fresh/separate/independent session|agent|reviewer|pair of eyes",
  "did not write the change … review", "reviewer must not be the author", etc.

## 5. COMMAND_TOKEN — allow arguments in backticked `python -m …` commands

- Before: `(python[0-9.]*\s+-m\s+\S+|pytest\b[^`\n]*|...`
- After:  `(python[0-9.]*\s+-m\s+\S+[^`\n]*|pytest\b[^`\n]*|...`
- Reason: underfire vs intent ("accepts backticked AND unformatted command
  forms"). The `python -m` alternative had no argument tail, so
  INLINE_CMD_RE required the closing backtick right after the module name;
  `` `python -m pytest tests/ -k rebalance` `` never matched as an inline command.
  Exposed by `b06_bad_no_refute.md`'s completion gate (wrongly failed
  names_runnable_oracle on an assertion expected to pass).

## 6. PREREG_RE — plain-register lead-ins and filename dots

- Before: `before (implementing|starting|making changes|acting|writing (any )?code|each (change|unit|step)|touching)[^.\n]{0,120}(write (down|out)?|record|state|document|note)[^.\n]{0,80}(expect|...)`
- After:  `before ((you |it |the agent )?(start|begin|touch|implement|act|proceed|mak|writ|chang)[a-z]*|each (change|unit|step))(?:[^.\n]|\.(?=\w)){0,120}(write (down|out)?|record|state|document|note)(?:[^.\n]|\.(?=\w)){0,80}(expect|...)`
- Reason: two underfires vs intent ("expected outcome/prediction recorded before
  implementation").
  (a) Plain-English lead-ins "before you start / before you touch anything,
  write down what you expect…" did not match the gerund-only verb list — this is
  exactly the register the arm-fairness rule requires the grader to credit.
  Exposed by `b07_good_plain.md`, `b12_good_plain.md`.
  (b) The `[^.\n]` gap filler treated the dot in a filename ("write down in
  NOTES.md what you expect") as a sentence boundary; the filler now permits dots
  followed by a word character (filenames) while still stopping at sentence-ending
  periods. Exposed by `b03_good_plain.md`.
  Cross-checked against all mutants expected to fail prereg (`b09_bad_no_prereg.md`)
  and against unrelated "before …" phrases in every bad file — no new false passes.

## Pilot calibration round (2026-07-14, pre-baseline; DESIGN §4 pilot protocol)

9 grader-vs-hand-label disagreements on the 4 no-skill pilot prompts, ALL
under-crediting plain-register phrasing (the predicted circularity failure).
Intents unchanged; regexes widened concept-faithfully; validity suite re-run
34/34 and pilot re-run to full agreement after:

- INTERACTIVE_RE: "ask him/her/them", "pause and ask", parenthetical-tolerant
  "owner (X) is available", blocker→ask.
- HONEST_FAILURE_RE: "negative/null result … successful outcome", "if you
  cannot fix/identify…", cannot→document/recommend forms, "do not thrash".
- GATE_LANG_RE: "confirm … passes/green".
- check_oracle: JOB_GATE_RE (a named CI job/workflow whose green status gates
  completion is a runnable oracle) + gate-flavored markdown-heading sections
  count as gate context for commands inside them.
- PREREG_RE: "write down X before changing anything", "decision rule",
  pre-committed sanity/abort gates ("abort … if any of") — adjudicated as
  genuine refutable-expectations-before-action.
- REGRESSION_FLOOR_RE: "previously-passing tests must still pass",
  "did not degrade".
- CRITERIA_FIRST_RE: "do not add or substitute criteria", "criteria …
  required/fixed/frozen".
- REPRO_FIRST_RE: "gather failure evidence (do this before changing
  anything)", "root cause identified from actual failure logs".
- REGRESSION_CHECK_RE: "do not disable or weaken the job", "job passes on
  that branch/after the change".

## Post-freeze fix (2026-07-14, after construction baseline grading; logged per DESIGN §0)

REGRESSION_FLOOR_RE missed "MUST-HOLD (floor)", "no <word> regression"
("no correctness regression"), and "must not break" — discovered by hand-audit
of the two with_skill OPT runs it failed. Intent plainly satisfied in both.
Widened; validity 34/34; pilot 0 mismatches; workspace re-graded (with_skill
skill-feature 71→73). No other entries changed.

## Post-freeze fix 2 (2026-07-14, pre-candidate; logged per DESIGN §0)

COMMAND_TOKEN gained `python[0-9.]* <script>.py` — `python3 score.py` is a
plainly runnable invocation the token could not see (candidate-review
finding, verified empirically). Validity 34/34, pilot 0 mismatches, baseline
workspace re-graded with the widened instrument before any candidate run so
all arms are compared on one grader.

## Post-freeze fix 3 (2026-07-14, candidate round 1 diagnosis; logged per DESIGN §0)

Candidate round-1 losses traced to a systematic instrument defect: the master
`\b(...)\b` wrapper rejects inflected forms ("fails", "baselines",
"demonstrated red"), plus missing concept vocabulary. All verified by running
the exact failing texts against the regexes. Widened, intent unchanged:
- HONEST_FAILURE_RE: + "unsettled" (explicitly-unsettled reporting IS the
  honest-failure concept).
- NEGATIVE_CASE_RE: inflection tolerance ([a-z]* on verb tails), + catch/guard.
- BASELINE_FRESH_RE: plural "baselines", verb-stem tolerance, window 80→100.
- SCOPE_RE: + never/do-not delete|remove|drop|relitigate, denylist/allowlist
  (a denylist is a scope boundary), will-not forms.
- REPRO_FIRST_RE: + "defect demonstrated red", "red before fix", "show it
  red ... apply", build-harness window 40→60.
Validity 34/34, pilot 0 mismatches. All arms re-graded on the widened
instrument before the candidate_2 margins run.
