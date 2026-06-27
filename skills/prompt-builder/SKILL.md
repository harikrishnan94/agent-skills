---
name: prompt-builder
description: Use when the user wants to author a rigorous, evidence-driven prompt for an unattended or interactive engineering task. Turns a modular skeleton into a concrete task prompt by selecting a task profile (BUILD/OPTIMIZATION/RESEARCH/DECISION/AUTHORING/REPAIR), filling slots, and pruning optional sections. Enforces pre-registration, ≥3 independent converging evidence sources for material claims, an auditable methodology log, and independent adversarial review.
---

# ============================================================================
#  UNATTENDED / INTERACTIVE ENGINEERING TASK — MODULAR PROMPT TEMPLATE  (rev. 2)
#  (select a PROFILE in §1; specialize the <<SLOTS>>; keep [CORE], drop [OPTIONAL])
# ============================================================================

# §0 · HOW TO SPECIALIZE THIS TEMPLATE  — read first, then delete this section
# ----------------------------------------------------------------------------
> BUILDER: You are turning this skeleton into a concrete task prompt. FILL slots and
> PRUNE; don't rewrite the scaffolding. Principles:
>
> 1. Pick a PRIMARY PROFILE in §1 first; it sets how the variable knobs (pre-registration,
>    iteration, evidence sources, acceptance) are read everywhere below. Units may override
>    it per-unit. The spine is identical across profiles; only the knobs change.
> 2. State CONTEXT, INTENT, GOAL precisely; leave the INVESTIGATIVE PATH open. Don't
>    enumerate every file/command/step — give a resource map (§13) and trust the agent to
>    find the path. Prescribe the PROCESS (evidence, iteration, review), not the route.
> 3. Keep all [CORE] sections. Drop [OPTIONAL] ones that don't apply; honor [CONDITIONALLY
>    CORE] when its trigger is present. Deleting a section is a decision — leave a one-line note.
> 4. Scale the EVIDENCE STANDARD (§9) via the profile and the materiality tier. The SHAPE is
>    invariant (material claims settle only on ≥3 independent converging sources, pre-
>    registration, no-result-on-disagreement); the SOURCES change with the profile.
> 5. Set the numbers your profile needs: iteration depth (§2), noise band (§9, quantitative
>    only), baselines, acceptance criteria, the risk tier that drives review weight (§12).
>    «DEFAULT»s are marked.
> 6. Run mode: pick UNATTENDED or INTERACTIVE in §2 and delete the other. The poll-don't-
>    block rule applies to both, but machine-waits and human-waits behave differently (§2.4).
> 7. After filling, re-read §15 (Definition of Done) and confirm every line maps to an
>    acceptance criterion you actually wrote, and that profile selection is the first thing
>    the executing agent confirms — not an afterthought.


# §1 · TASK PROFILE  [CORE]  — select a PRIMARY; units may override
# ----------------------------------------------------------------------------
> BUILDER: Choose the PRIMARY profile. It defines, for the rest of the prompt, what
> "pre-register," "acceptance," "evidence sources," and "iterate" concretely mean. The
> structure does not change between profiles — these are the dials.
>
> Real tasks often span profiles (a fix needs RESEARCH to root-cause, BUILD to patch,
> OPTIMIZATION to confirm no regression). So: each work unit in §6 MAY declare a narrower
> UNIT PROFILE that governs ITS pre-registration / evidence / iteration / acceptance only;
> if omitted, the unit inherits the primary. A mixed-profile task MUST state how evidence
> from one unit gates the next (§6).

PRIMARY PROFILE: <<BUILD | OPTIMIZATION | RESEARCH | DECISION | AUTHORING | REPAIR>>

- **BUILD / FEATURE** — produce a new capability.
  - Pre-register = expected behavior + the acceptance test that proves it.
  - Acceptance = behavior matches spec; positive AND negative cases tested; teardown clean.
  - Evidence sources = the oracle/test suite + an independent cross-check + edge-case exercise.
  - Iteration = review-driven: no artificial floor; never return on an open blocking item.

- **OPTIMIZATION / REFINEMENT** — improve a measured property of something that works.
  - Pre-register = expected MECHANISM + predicted MAGNITUDE.
  - Acceptance = a MUST-HOLD floor (no regression within noise) + the measured WIN, reported
    separately. A win valid only in the target regime but neutral in the test regime is still
    worth pursuing — if measured and stated honestly.
  - Evidence sources = the named instruments in §9.2.
  - Iteration = ≥<<N=3 «DEFAULT»>> evidence-based hypothesis cycles before returning.
  - Noise band (§9.4) applies.

- **RESEARCH / INVESTIGATION** — answer a question or find a root cause.
  - Pre-register = the hypothesis + what would CONFIRM and what would REFUTE it.
  - Acceptance = question answered with converging evidence, or honestly reported open/NO RESULT.
  - Evidence sources = independent methods / datasets / reference implementations that fail
    differently.
  - Iteration = until evidence converges or the question is settled; log null results.

- **DECISION / ANALYSIS** — evaluate options and recommend.
  - Pre-register = the comparison criteria + how each is scored, written BEFORE scoring (so the
    conclusion can't pick its own yardstick).
  - Acceptance = options compared on the pre-registered criteria; recommendation justified;
    rejected options retained with reasons.
  - Evidence sources = ≥3 independent sources per material criterion.
  - Iteration = until each criterion is grounded; revisit if a source contradicts.

- **AUTHORING / DOCUMENTATION** — produce a written/structured artifact.
  - Pre-register = the outline/scope + the sources that establish each claim's correctness.
  - Acceptance = scope covered, claims accurate, conforms to the project's conventions.
  - Evidence sources = cited sources + an independent fact-check + a review pass.
  - Iteration = review-driven, as BUILD.

- **REPAIR / DEBUGGING** — restore intended behavior or remove a defect.
  - Pre-register = the suspected fault model + the evidence that would confirm/refute it.
  - Acceptance = defect REPRODUCED first where possible; fix demonstrated by the regression
    oracle; no adjacent regression. A patch that only masks the symptom is rejected unless the
    symptom-mask is explicitly accepted in the Decision log with rationale.
  - Evidence sources = the failing reproduction + the corrected oracle/test + an independent
    path / reference / static-or-dynamic check.
  - Iteration = root-cause-driven; do not ship on a symptom mask by default.


# §2 · MISSION & OPERATING MODE  [CORE]
# ----------------------------------------------------------------------------
You are executing <<TASK_NAME>>. <<ONE PARAGRAPH: what gets delivered and why it matters.>>

Run mode: <<UNATTENDED | INTERACTIVE>>.

Deliver the work unit(s) in §6 end to end, in the stated order, and PROVE each material
claim with converging evidence to the standard in §9. <<STATE CONSTRAINTS: greenfield/
experimental (anything may change to serve the Goal) OR production (name the compatibility
constraints).>>

When an ambiguity arises, exercise your own judgement and choose the option that most closely
serves the Goal (§5). Either way, record the call in the Decision log (<<DECISION_LOG_PATH>>,
id <<D-####>>, template §14) and proceed on the best-aligned default — do not stall.

The one exception is a decision that is materially scope-changing or hard to reverse. In
INTERACTIVE mode, surface that one to the user before proceeding (per the human-wait rule in
§2.4 — ask once, smallest decision surface). In UNATTENDED mode there is no one to ask: proceed
on the best-aligned default, but flag the entry as a HIGH-IMPACT assumption so it is reviewed
on return, and treat it as a revisit trigger.

Hard process rules (in addition to §9):

1. **Minimum iteration depth** — as the unit's profile defines (§1). OPTIMIZATION/RESEARCH
   carry a floor of ≥<<N>> evidence-based cycles before returning; BUILD/DECISION/AUTHORING/
   REPAIR are review-driven (close every blocking item; never return on a failing gate). One
   pass then declaring victory, where the profile expects exploration, is a task failure.
2. **Auditable methodology log.** Maintain <<METHODOLOGY_LOG_PATH>> (template §10), append-
   only. Every experiment, change, and check gets an entry. Log failed and null results too.
   The log is a primary deliverable.
3. **Think holistically before acting locally.** Before each iteration, write down (in the
   log) how the change affects the WHOLE system, not just the local part. A local win that
   pessimizes the whole is a regression.
4. **Never block — but machine-waits and human-waits differ.**
   - **Machine waits** (builds, measurements, background jobs): poll progress/liveness at
     ~<<30s>> intervals, keep independent work moving, and kill + diagnose anything clearly
     hung. Never stall on a job that may have finished or died.
   - **Human waits** (INTERACTIVE decisions): ask ONCE with the smallest necessary decision
     surface; do not "poll" a person or invent progress while waiting. If continued execution
     is required, record the assumption in the Decision log and proceed on the best-aligned
     default rather than stalling.


# §3 · SOURCE CONTROL & CHANGE DISCIPLINE  [OPTIONAL — code tasks]
# ----------------------------------------------------------------------------
> BUILDER: Drop for non-code work. Fill repos/branches; keep the rules.

Scope spans <<N>> repo(s). Make changes directly on <<BRANCH(ES)>> — no new feature branches,
worktrees, or detached HEADs. Verify the branch before each commit.

- Land work as **small, reviewable commits** — one logical change each. Suggested seams:
  <<LIST IN ORDER>>. Not one mega-diff.
- **Never commit on red.** Run the gates + build for the touched repo before each commit.
- Descriptive messages: what + why, the <<D-####>> it implements, the gate that proved it.
  Commit the pre-registration / methodology-log / report / evidence artifacts alongside the
  code they document — branch history is itself the audit trail.
- Git safety: never touch git config; no force-push; no rebasing/amending pushed commits;
  do not push unless explicitly asked.


# §4 · CONTEXT  [CORE]
# ----------------------------------------------------------------------------
> BUILDER: Describe current state precisely enough to orient, then tell the agent to
> RE-VERIFY rather than trust. Name components, current behavior, the baseline/reference it
> must match/beat/answer. Don't smuggle in the solution.

<<CURRENT STATE — VERIFIED, BUT RE-VERIFY; DO NOT TRUST BLINDLY.>>
<<KEY COMPONENTS AND HOW THEY INTERACT.>>
<<THE BASELINE OR REFERENCE (what it is + how established) — instruct the agent to RE-ESTABLISH
it fresh on its own state.>>
<<EXISTING ASSETS / PRIOR ART WORTH STUDYING FIRST.>>


# §5 · GOAL (NORTH STAR)  [CORE]
# ----------------------------------------------------------------------------
> BUILDER: State the intention(s). If two appear to conflict, name the reconciling design
> choice in §7 (now conditionally core). Distinguish the MUST-HOLD constraint from the payoff.

<<INTENTION 1.>>
<<INTENTION 2 (if any), and the apparent tension.>>
<<THE MUST-HOLD CONSTRAINT vs THE REAL PAYOFF.>>


# §6 · WORK UNITS & HOW THEY CONVERGE  [CORE]
# ----------------------------------------------------------------------------
> BUILDER: Break the task into the smallest set of units that can be executed and proven in
> sequence. For each: a one-paragraph scope + the HONEST expected outcome (incl. "neutral
> here, value shows elsewhere" if true) + its UNIT PROFILE if it differs from the primary +
> its RISK TIER (drives review weight, §12). For mixed-profile tasks, state explicitly how
> each unit's evidence GATES the next. Expand each into a §8 block.

Execute in order: <<UNIT 1 → UNIT 2 → … >>.
- **Unit 1 — <<NAME>>** (<<role: precursor/core/refinement>>; profile: <<inherit|…>>; risk:
  <<low|high>>). <<scope + honest expectation + what it gates.>>
- **Unit 2 — <<NAME>>** <<…>>


# §7 · KEY DESIGN TENSION / BINDING CONSTRAINTS
#      [CONDITIONALLY CORE — required when §5 has a tension, a prior binding finding, or an
#       accepted tradeoff; otherwise OPTIONAL]
# ----------------------------------------------------------------------------
> BUILDER: Make prior findings BINDING; tell the agent to read them before pre-registering.
> List accepted tradeoffs so they aren't relitigated — nor used to excuse hiding a real defect.

<<THE RECONCILING CHOICE AND WHY IT WORKS.>>
<<BINDING PRIOR FINDINGS (path + what's settled).>>
<<ACCEPTED TRADEOFFS, each logged: what we give up, what we get, why acceptable.>>
<<MANDATORY CAVEATS — things that look trivially true but aren't; pretending they are is a
banned unproven causal story.>>


# §8 · PER-UNIT SPECIFICATION  [CORE — repeat per work unit]
# ----------------------------------------------------------------------------
## Unit <<X>> — <<NAME>>   (profile: <<inherit|…>>; risk: <<low|high>>)

**Scope.** <<What changes; what explicitly does NOT change here. Keep units separate — do not
pull a later unit's work in to dodge this one's honest result.>>

**Acceptance criteria.** <<Concrete, checkable, in the unit profile's terms (§1). Separate
MUST-HOLD from the GOAL. [OPTIMIZATION: where a bounded regression is acceptable here but
recovered later, say so and PRE-REGISTER the bound — exceeding it blocks the unit.]>>

**Pre-register (before acting)** in <<PREREG_PATH>>, per the unit profile: the expected outcome
AND how you'll know (the evidence that would confirm/refute it). A prediction/result mismatch is
a finding to investigate, never to rationalize post-hoc.


# §9 · NON-NEGOTIABLE EVIDENCE STANDARD  [CORE]  (this is the point of the exercise)
# ----------------------------------------------------------------------------
> BUILDER: Keep 9.1, 9.3–9.7. FILL 9.2 with sources appropriate to the profile (examples below).
> Keep the "material claims settle only on ≥3 independent, convergence-or-no-result" shape always.

**9.1 — Material claims settle only on convergence; route everything else by tier.**
- A **MATERIAL claim** is any claim used to satisfy acceptance criteria, assert correctness /
  safety / performance / a measured property / causality-mechanism, justify a recommendation,
  close a blocking review item, or declare a unit green. **No material claim may be stated as
  settled unless ≥3 INDEPENDENT sources converge** (§9.2) — agree in direction and, where
  quantitative, roughly in magnitude.
- An **OPERATIONAL observation** is a direct report of an artifact, command output, file path,
  version, or raw result. It needs a cited source or a reproduction record — NOT three sources —
  unless it later becomes material to acceptance, at which point it must be re-proven under this
  section.
- A **LEAD** is an explicitly-unsettled suspicion or hypothesis (§12 vocabulary). It may be
  reported with partial evidence but MUST NOT be used to satisfy acceptance. (LEAD is the single
  name for unsettled findings everywhere in this prompt — reviewers and implementer alike.)

**9.2 — Independent = a different source that can fail differently** — not three re-runs of one
tool, not three quotes of one author. Triangulate across as many as the environment allows
(named for this task):
- <<SOURCE CLASS 1>>  - <<SOURCE CLASS 2>>  - <<SOURCE CLASS 3>>  - <<4 / 5 optional>>
> BUILDER — starting points by profile (replace with what actually exists here):
>  BUILD: unit/integration oracle · independent negative/edge exercise · static/dynamic analysis ·
>    reference implementation · manual end-to-end check.
>  OPTIMIZATION: benchmark timing · profiler/call-stack · low-level counters · production-like
>    telemetry · microbench isolating the mechanism.
>  RESEARCH: independent dataset · independent method · reference implementation · primary source ·
>    replication attempt.
>  DECISION: primary source · independent empirical data · expert/industry source · internal
>    constraint · a counterexample/source AGAINST the preferred option.
>  AUTHORING: primary citation · independent secondary source · fact-check pass · project-convention
>    sample · reviewer verification.
>  REPAIR: failing reproduction · corrected oracle/test · independent code path · static/dynamic
>    check · bisection/diff against last-known-good.
Use sources to establish the MECHANISM / the WHY, not just the outcome.

**9.3 — Pre-register before gathering acceptance evidence** (<<PREREG_PATH>>): the expected
outcome and the confirm/refute evidence (the profile fixes the exact form). Then gather it. A
mismatch is a finding to investigate. (Discovery before pre-registration is allowed — see §11.)

**9.4 — If sources disagree, you have NO result yet.** Root-cause the discrepancy (noise, wrong
baseline, selection bias, instrument/source artifact) before asserting anything. For QUANTITATIVE
claims the effect must exceed the noise band := relative diff ≤ <<max(5%, 1 stdev) «DEFAULT»>>; if
within noise, say exactly that.

**9.5 — Control the confounders.** <<Hold constant whatever could confound the comparison — idle
host / fixed inputs / identical config across compared modes / stated warm-vs-cold; non-perf:
same dataset, same definitions, same reference version.>> Re-establish EVERY comparison point
FRESH on the SAME artifact in the SAME session. Record exact commands + env + versions
(<<REPRODUCTION_PATH>>).

**9.6 — BANNED moves:** "should work" / "probably" / "I think this helps", any unproven causal
story, single-run numbers, cherry-picked results, claiming a win from outcome alone with no
mechanism source, claiming a cost/defect was eliminated without a source proving it, **hiding or
down-playing a known deviation or defect** (a measured-and-documented deviation is fine; a silent
one is a failure), and declaring done without the correctness oracle. If you catch yourself
writing one, stop and get evidence.

**9.7 — Stop condition (no forced closure).** If a material claim cannot reach convergence within
the available budget/environment, return **NO RESULT** for that claim — with the best current
leads, the evidence gaps, and the specific next source that would settle it. Do NOT manufacture
weaker evidence to force closure, and do NOT silently drop the claim.


# §10 · AUDITABLE METHODOLOGY LOG  [CORE]
# ----------------------------------------------------------------------------
Maintain <<METHODOLOGY_LOG_PATH>>, append-only — never edit after the fact (corrections are new
entries referencing the old). Per entry:

~~~
### L#### — <short title>  [unit <X>]  [iteration N]  <ISO-8601 timestamp>
- Goal / hypothesis: what I expected + the pre-registered prediction (link the prereg line).
- What I did: the concrete change/experiment (files touched, commits/versions).
- How I did it: mechanism + exact, copy-pasteable commands.
- How verified: which ≥3 independent sources (for material claims), with exact invocations.
- Result: RAW outputs — or, when too large, PATHS to raw artifacts with a hash, command id,
  timestamp, and a concise excerpt sufficient to identify the relevant result. (Numbers/medians
  +spread, counter or comparison tables — not prose summaries standing in for data.)
- Interpretation: what it means; does it converge? noise vs effect; prediction vs observation.
- Learnings: what this changes about the design / next step / whole-system picture.
- Verdict: DONE (criterion met, evidence converges, review-ready) or CONTINUE (next hypothesis →)
  or NO RESULT (per §9.7, with the settling source named).
~~~


# §11 · PER-UNIT EXECUTION LOOP  [CORE]
# ----------------------------------------------------------------------------
**Discovery (allowed before pre-registration).** Before step (a), you MAY orient — read the
code/data, establish baseline behavior, find the available tests, map the schema, surface
candidate hypotheses. Discovery output is ORIENTATION, recorded in the log as such; it is NOT
acceptance evidence unless re-gathered after pre-registration. Pre-register from understanding,
not from guesswork.

Then, for each work unit (in order) and each iteration within it:

a. **Restate** scope + acceptance. **Pre-register** per the unit profile. Write the holistic
   end-to-end impact note (§2.3) in the log.
b. **Implement / investigate** per spec. Write/extend the oracle + tests first where it fits.
   Keep the change minimal and reviewable.
c. **Correctness gate** — run the regression oracle(s) and the unit's checks. The oracle must
   prove the intended thing actually happened, not a trivial pass. **If red:** gather only
   DIAGNOSTIC evidence, explicitly labeled — red-state evidence may diagnose the failure but may
   NOT satisfy acceptance or claim success. Fix and repeat; never close a unit on red.
d. **Gather evidence** for the unit's material claims across ≥3 independent sources (§9.2).
   Produce an evidence log with RAW outputs (or referenced artifacts per §10): exact commands,
   env, raw results, the deliverable-specific tables (§14), prediction-vs-observation.
e. **Independent adversarial review** (§12) — at the cadence and weight §12 specifies.
f. Loop to (b)/(c)/(d) if the review raises a blocking item, OR evidence does not converge, OR an
   acceptance criterion is unmet, OR the profile's iteration depth (§2.1) is unmet. Else mark the
   iteration green and proceed.


# §12 · INDEPENDENT ADVERSARIAL MULTI-AGENT REVIEW  [CORE]
# ----------------------------------------------------------------------------
**When to review (cadence).** Run review after each UNIT ITERATION before marking it green, and
once more before FINAL DELIVERY. Also run it after any high-risk, irreversible, or safety-
sensitive change. Do NOT run a full review after every low-level command — only when a step
materially changes the artifact, the evidence base, or the risk profile.

**How heavy (review weight by risk tier, §6).**
- **Low-risk unit:** a SINGLE adversarial pass covering all axes below (one subagent, clean
  context) is sufficient. Escalate to the full fan-out only if that pass surfaces a blocking item
  or a safety lead.
- **High-risk / safety-sensitive / irreversible unit:** the FULL fan-out — Agents A–D (plus any
  optional axis) as separate isolated subagents, then a synthesis reviewer.

Reviewers did NOT do the work. Each gets ONLY the SPEC (this prompt + the unit's acceptance
criteria), the ARTIFACT under review, and the EVIDENCE STANDARD (§9) — never another reviewer's
context or findings. Independence is the point: uncorrelated reads beat consensus that formed too
early. When all return, the synthesis reviewer receives all reports.

## Shared mandate (all reviewers)
You are adversarial in what you HUNT: assume the implementer was over-optimistic and that the work
FAILS on your axis; try to prove it. You are disciplined in what you ASSERT: every claim you make
is held to §9 exactly as the work itself is. Inspect the actual artifact; never trust the SPEC's
description of what it does.

A suspicion you can't yet substantiate to §9 is filed as a **LEAD** — explicitly labeled, with the
one source you have and the specific independent source that would confirm or kill it. It is never
promoted to a FINDING by conviction. §9's banned moves bind you too. Rank by impact; if after real
effort you can't substantiate a failure on your axis, say so plainly rather than manufacture nits.

### Agent A — Correctness & Safety
Does the work do what the SPEC requires, and is it DEMONSTRATED? A "this is a bug" claim is a
correctness claim: it must reproduce against an oracle, not merely trace plausibly. Cover
spec-behavior match, edge/error/unhappy paths, and that tests prove valid inputs succeed AND
invalid inputs fail. Distinguish genuinely-exercised branches from nominally "covered" ones.
Untested branches and missing negative cases are findings; an arguable-but-unreproduced defect is
a LEAD.
**Safety (same evidence bar):** does the work preserve safety invariants —
- resource cleanup on ALL paths (success, error, cancel): no leaked memory, handles, sockets,
  workers, locks;
- memory & concurrency safety: bounds, lifetime/use-after-free, races, deadlock (re-derive any
  liveness/ordering invariant the change touches);
- numeric/precision safety where a bound matters: overflow, truncation, silent precision loss;
- failure behavior: errors propagate and the system fails safe, not silent/corrupt;
- trust boundaries: external/untrusted input validated before use; no unsafe deserialization,
  injection, or path/permission escalation; no data loss or corruption.
A safety defect asserted must reproduce or be filed as a LEAD with the source that would settle it.
Where the SPEC names accepted tradeoffs (§7), check they're honored and not used to mask a genuine
safety defect.
> BUILDER: prune safety sub-bullets to the ones that exist in this domain; add any domain-specific
> invariant (idempotency, exactly-once, data integrity, access control, …).

### Agent B — Simplicity
Could a competent but unremarkable engineer read this, understand it now, and change it safely in
six months? Hunt incidental complexity, cleverness that buys nothing, abstractions costing more
than they earn, anything that could be plainly dumber. Separate inherent complexity (justified)
from accidental (a finding). If you argue a simplification is "free," that it costs no correctness
or required property is itself a claim — evidence it or label it a LEAD.

### Agent C — Performance & Mechanism  [keep for OPTIMIZATION; OPTIONAL otherwise]
Against the time/memory/throughput the SPEC actually asks for, does it hold up? Every regression /
complexity-class / resource / hot-path claim is fully bound by §9: ≥3 converging independent
sources across DIFFERENT classes, pre-registered mechanism + magnitude, effect clearing the noise
band, mechanism SHOWN not just outcome. Attack any "eliminated cost" claim: is it actually gone, or
merely deferred/relocated? Don't invent requirements the SPEC doesn't state. If you can't measure
here, return pre-registered LEADS, not findings.

### Agent D — Style & Conventions
Does the work conform to THIS project's established conventions — judged against what the
surrounding artifact already does, not personal taste or a generic guide? Cite the convention and a
place the project already follows it. Don't justify a style call with an unproven performance story.

> BUILDER — OPTIONAL EXTRA AXIS (bind to §9): Agent E — Holism: does the local win help or hurt the
> WHOLE system under the real (not micro) regime? Memory/lifetime correct, nothing unbounded?

### What each reviewer returns
For every item: stable id; axis; **type (FINDING | LEAD)**; **claim class (behavioral / safety /
performance / mechanism / regression / style / simplicity)**; severity (blocking / should-fix /
minor); location; and —
- if FINDING on an empirical class: the **≥3 converging sources** named individually with
  direction/magnitude, the pre-registration if relevant, the noise-band check;
- if LEAD: the single source held + the specific independent source that would settle it; **and
  whether it is a BLOCKING LEAD** (criteria below);
- reasoning + a concrete suggested change.
Then a one-line axis verdict. An empty list + a note on what was checked is a valid result.

**Blocking lead (the one case an unproven suspicion still gates shipment).** A LEAD may be marked
**blocking** only when ALL hold: (i) the suspected issue would be safety-critical, data-corrupting,
or acceptance-invalidating IF true; (ii) the reviewer states a PLAUSIBLE MECHANISM, not a bare
"feels risky" (a blocking lead without a mechanism is downgraded to an ordinary lead); and (iii)
the settling evidence is reasonably obtainable within the task's budget/environment. A blocking
lead does not become a finding without §9 evidence, but it blocks shipment until resolved,
downgraded with evidence, or explicitly RISK-ACCEPTED in the Decision log with rationale + owner.
The risk-acceptance path MUST stay reachable (incl. <<[UNATTENDED]>>: record acceptance in the
Decision log and proceed) so a lead can never deadlock the run.

## Synthesis reviewer
You receive all reports and are bound by §9 and its banned moves. Emit one coherent, internally
non-conflicting review:
- Merge duplicates. Where two axes pull opposite ways (simplicity vs performance, safety vs speed),
  resolve ON EVIDENCE against the SPEC — the side meeting §9 wins; state the tradeoff and the basis.
  You may not break a tie by assertion. **Safety findings that meet the bar are not traded away for
  performance.**
- You may NOT promote a LEAD to an accepted finding. Surface leads separately as "needs evidence,"
  flagging any BLOCKING lead and the source that would settle it.
- **ACCEPTED:** the final actionable list, severity-ordered, each with location, rationale,
  suggested change, and (for empirical items) its converging sources. Must not self-contradict.
- **REJECTED:** every finding/lead dropped or overruled, each with its reason — including "does not
  meet the evidence standard (only N independent sources / within noise / speculative /
  unreproduced)" where that applies. Nothing disappears silently.
- **Bottom line:** ship / ship-with-fixes / needs-rework, listing blocking items (findings AND
  blocking leads). No "ship" without the correctness oracle satisfied, no open blocking safety
  finding, and no unresolved blocking safety lead (unless risk-accepted per above).

Record the verdict + blocking items in <<ADVERSARIAL_REVIEW_PATH>>. A unit/iteration is green ONLY
after review passes.
> WIRING: give the synthesis agent the strongest model. If the harness can't truly isolate the
> reviewers, at minimum withhold each one's output from the others until all have returned; if it
> can't spawn isolated subagents at all, run the single adversarial pass with an explicit note that
> independence is degraded, and weight its leads accordingly.


# §13 · RESOURCE MAP  [CORE]
# ----------------------------------------------------------------------------
> BUILDER: Give verified STARTING POINTS, not a route. Tell the agent to re-verify.

<<HARNESS / DRIVERS (how to run the work + read results).>>
<<CONVENTIONS TO MIRROR (where prior units put pre-reg, reproduction, evidence, reports).>>
<<KEY COMPONENTS (the few entry points worth naming), per side/repo.>>
<<PRIOR ART / REFERENCE IMPLEMENTATIONS to study first, incl. anything usable as an oracle.>>
<<REGRESSION ORACLES + TEST LOCATIONS.>>
<<ENVIRONMENT OF RECORD (host, versions, ports, caps) — re-confirm + re-record at pre-registration.>>


# §14 · DELIVERABLES  [CORE]
# ----------------------------------------------------------------------------
1. The work landed as <<small reviewable commits on <<BRANCHES>> | the concrete artifact>>, with
   its observability/instrumentation where applicable.
2. Green correctness gates (regression suite + task oracles) in the new mode.
3. <<PREREG_PATH>> — expected outcome + confirm/refute evidence, written FIRST.
4. Evidence log with RAW outputs (or referenced artifacts per §10) across ≥3 source classes, the
   deliverable-specific tables (<<comparison / budget / option-scoring, as the profile needs>>),
   each with prediction-vs-observation, PLUS an **evidence matrix** mapping every MATERIAL claim to
   its sources (a navigation/audit aid — locating evidence, not a substitute for the §9 independence
   check):

~~~
| Claim ID | Material claim | Source 1 | Source 2 | Source 3 | Converge? | Noise/confounder check | Verdict |
| -------- | -------------- | -------- | -------- | -------- | --------- | ---------------------- | ------- |
~~~

5. <<METHODOLOGY_LOG_PATH>> — complete append-only log (≥<<N>> iterations where the profile
   requires), including failed/null/NO-RESULT entries.
6. <<ADVERSARIAL_REVIEW_PATH>> — a passing synthesis (or single-pass) verdict per reviewed step.
7. Decision-log entries (<<D-####>>) for every judgement call, documented deviation, and risk
   acceptance, in this format:

~~~
### D-#### — <decision title> — <ISO-8601 timestamp>
- Context:
- Options considered:
- Criteria:
- Chosen option:
- Rationale:
- Evidence (or NO RESULT + settling source):
- Risks / tradeoffs (incl. any risk-accepted blocking lead + owner):
- Revisit trigger:
~~~

8. <<REPRODUCTION_PATH>> — exact commands, env, versions, config, build/run recipe.
9. A REPORT.md per unit with the GREEN verdict and a closing note on each Intention (§5): how close
   the goal is, with the measured delta / answer and its mechanism.


# §15 · DEFINITION OF DONE  [CORE]  (all required)
# ----------------------------------------------------------------------------
> BUILDER: one line per unit mapping to its §8 acceptance; confirm each has evidence behind it.

- <<Unit X green: <criteria>, oracle passes, no new defect, clean teardown, material claims
  converge, review passed, NO open blocking finding AND no unresolved blocking safety lead (unless
  risk-accepted with rationale + owner in the Decision log).>>
- The unit profile's iteration depth met (≥<<N>> cycles where OPTIMIZATION/RESEARCH; all blocking
  items closed where BUILD/DECISION/AUTHORING/REPAIR).
- Every MATERIAL claim backed by ≥3 independent converging sources or returned as NO RESULT with
  its settling source named; every deviation logged; reproduction recorded.
- <<For code tasks:>> all work committed as small reviewable patches on <<BRANCHES>> — each commit
  green, no mega-diff, history is the audit trail.
