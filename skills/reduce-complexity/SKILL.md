---
name: reduce-complexity
description: >-
  Report-only structural review of an in-progress change — a PR or feature
  branch — that finds accidental complexity accreted while the change was
  built and reports evidence-backed simplifications without applying any
  edits. Use when the user says "reduce complexity", "simplify this PR",
  "clean up this branch before review", "did this change accrete cruft", or
  asks whether an in-review change could be expressed more simply. Not for
  line-level style cleanup (humanize) or bug-hunting (code review).
---

# Reduce complexity: find what the change no longer needs

You are reviewing an in-progress change to find where it could be expressed
more simply if it had been designed from the start knowing where it ended up.
Changes are built incrementally — fixes that get them working are not always
folded back into the design — and your job is to find that residue while the
change is still open.

Three properties govern everything below:

- **Report-only.** Never apply edits; the repository tree is read-only for
  this skill — git commands and file reads only. The product is a report.
- **Base-commit-scoped.** Every finding lives in the diff between the branch
  and an explicitly established base commit, not in the codebase at large.
- **Structural.** Line- and function-level tells — comment noise, defensive
  theater, naming — are the `humanize` skill's territory; bug-hunting and
  applied fixes belong to code-review tooling. This skill judges how the
  change is put together.

## Hard rules

These bind every step below; when a rule and an apparent finding conflict,
the rule wins.

- A guard, check, fallback, or error handler may be flagged **only with an
  impossibility proof**: enumerate every caller, constructor, and type
  constraint (file:line) showing the guarded state unreachable. Where callers
  cannot be enumerated — public API, dynamic dispatch, deserialization,
  concurrency — classify it inherent and move on. Reflexively stripped
  defensive code is the canonical unsafe simplification.
- **Defense in depth is intentional.** At security, auth, and fraud
  boundaries, even a provably redundant check may be deliberate
  belt-and-suspenders against bugs in other layers. The verdict there is
  "label it or ask the author" — never "remove".
- **Hyrum's Law.** At an externally consumed surface, unspecified observable
  behavior — ordering, error strings, serialized formats — is behavior
  someone depends on. Externally consumed means inherent, automatically.
- **Distrust metadata, in both directions.** Comments and commit messages are
  claims to verify, not ground truth: "needed for backwards compat" does not
  suppress a finding until the code confirms it, and "temporary hack" does
  not create one.
- **Coverage gates confidence.** A behavior-preservation claim about code no
  test exercises is speculative by definition. Check whether tests cover each
  finding's behavior, say so in the finding, and demote findings over
  uncovered code.
- **Line count is not the metric.** A correct simplification may add
  functions; the measure is fewer entangled concerns, less state, fewer
  interacting branches. Extraction is not the default fix — inlining is
  equally a simplification, and a long linear function is often already the
  simple form.
- Never rate confidence numerically; a finding is justified by the evidence
  category it rests on. If you are not certain a simplification preserves
  behavior, do not report it — false positives erode the trust the report
  depends on.
- **Never flag:** shapes that read as complex but are the clean alternative —
  flat switch/table dispatch however long, guard-clause early returns, many
  small functions, long single-operator boolean chains, named intermediate
  variables, the language's own idiom (Go's repeated `if err != nil`),
  deliberate duplication in tests (tests favor clarity over DRY); mechanical
  territory — generated code, vendored dependencies, migrations, lockfiles,
  anything a linter or formatter owns; and pre-existing complexity the diff
  merely touches, which goes in its own report bucket, never mixed with
  findings about the change.

## Step 1 — Establish the change set

Fix the scope first: the diff between the current branch and a base commit.

1. **PR branch (preferred).** Find the current branch (`git rev-parse
   --abbrev-ref HEAD`) and check for an associated pull request (`gh pr
   view`, or the host's tooling). If one exists, the base commit is
   `git merge-base HEAD <pr-base-branch>`; continue to Step 2.
2. **Non-PR branch.** Derive the base: the upstream merge-base
   (`git merge-base HEAD @{upstream}`) if an upstream is set; else the
   merge-base with whichever integration branch exists (`main`, `master`,
   `develop`, `trunk`); else the divergence point from
   `git log --first-parent` and the reflog. When the user named a base or
   the derivation is unambiguous, state the base commit and the assumption
   and proceed; when candidates genuinely compete, ask — the entire review
   scope depends on it.

The changed lines are the primary scope. Read surrounding code, call sites,
and tests as needed — a shape that looks redundant in the diff may be
load-bearing once you see how it is used.

## Step 2 — Read the review

When a PR exists, read its review comments, human and bot alike. The
substance of accepted feedback is a hard constraint: a shape that exists to
satisfy a review comment is not accidental complexity, however awkward it
looks in isolation. The reverse does not hold — most review-round reshaping
never gets a comment, so the absence of one is not evidence that a shape is
unjustified or safe to remove. Judge from the code and behavior; treat the
thread as one input. Non-PR branches skip this step.

## Step 3 — Read the branch history as evidence

The verdict is always on the final state, but the commit sequence is
evidence you have nowhere else: a helper, parameter, or branch introduced at
commit k whose reason had disappeared by the final commit is the accretion
signature, and hunks reworked across three or more commits or review rounds
are where it concentrates — scan those first.

Check that the history is real before reading it: squashing and rebasing
make commit order no longer construction order. A single-commit branch or
freshly rebased history means the archaeology is unavailable — rely on
final-state evidence alone, and never narrate a construction story the
history cannot support.

For diffs above roughly 50 files, don't spread attention uniformly:
prioritize the most-churned files (`git log --oneline --since=6.months --
<file>`), where complexity costs the most.

## Step 4 — Scan for candidate shapes

Build an inventory of the diff — files, hunks, new symbols, new branches,
new parameters — then scan it one shape at a time. Collect candidates
without judging them yet; judgment is Steps 5 and 6.

| Shape | Detection evidence | Mechanical fix |
|---|---|---|
| Adapter between two halves of the same change | both shapes introduced by this diff | unify the shapes, delete the adapter |
| Constant-threaded flag or parameter | every call site passes the same literal | remove the parameter, delete the dead arm |
| Dead scaffolding from iteration | zero references in the final tree (grep, tests included); consumer deleted by a later commit of this branch | delete it |
| Unearned indirection | delegate-only wrapper with one caller; hook or generic with one user and no second-variant test (exempt test seams and public API) | inline / collapse |
| Wrong abstraction | call sites pass flags to fight a helper introduced here | inline it back into its callers — duplication is cheaper than the wrong abstraction |
| Within-diff duplication | side-by-side blocks both added here; worse when one clone was edited and its sibling was not | single point of truth — only when no mode flag is needed |
| Special case the general path handles | a traced execution of the input through the general path, not "looks equivalent" | delete the branch or hoist it to the caller |
| Redundant re-check on a dominated path | dominance argument plus caller enumeration; never at trust boundaries (hard rules) | remove the inner check |
| Policy strewn through conditionals | the same predicate tested at two or more new sites | decide once at the boundary |
| Derivable mutable state | the value is a pure function of existing inputs | compute on demand; perf-motivated → accidental-but-justified |
| Repo-relative reinvention | an existing helper, named, call-compatible | call the existing one |
| Stale narrative | names or comments describing a mechanism a later commit replaced | rename, rewrite the comment |
| Tangled ride-along | hunks with no def-use link to the change's purpose | recommend splitting out — never silent deletion |

## Step 5 — Verdict: three tests, three outcomes

Run each candidate through three tests:

1. **Re-derivation.** If the author rewrote the change in one sitting from
   the final requirement, would this construct exist? Constructs that only
   make sense given the order the branch was built are accidental by
   construction.
2. **Requirement.** Name the observable requirement the construct serves. If
   you cannot name one, the verdict is "ask the author" — never "removable";
   a shape can be the residue of two requirements interacting.
3. **Availability.** Accidental means avoidable with means already at hand.
   Name the means: the existing repo helper, the stdlib call, the
   established idiom.

Three verdicts, not two:

- **Accidental, removable** — report it with the cleaner shape.
- **Accidental but justified** — caches, measured denormalization, and other
  performance shapes: recommend isolating and labeling it, not deleting it.
- **Ambiguous** — phrase it as a question that names the evidence that would
  settle it.

Presume inherent unless proven redundant within this change: sad-path,
retry, and telemetry code; security and fraud checks; concurrency, overflow,
and NULL handling; external-interface conformity; compatibility shims; i18n
and legal requirements; anything a reviewer asked for.

## Step 6 — Verify before reporting

Try to refute each candidate; a refutation is worth as much as a
confirmation. Read the unchanged surroundings, every call site, and the
tests before judging. A surviving finding rests on a named evidence
category — caller enumeration, equivalence trace, zero-reference grep,
both-shapes-introduced-here. "Looks redundant" is not evidence.

Cross-check the hard rules and test coverage last, then apply the survival
bar: could you defend this finding to the author with file:line citations?
Most candidates should die here; a short or empty report means the change is
clean, and saying so is a correct outcome. Where the host supports it,
verify findings in a fresh pass — a new session or a second reviewer — since
the context that found a candidate tends to defend it.

## The report

Each finding, in this structure:

- **Title** — one specific sentence: what becomes simpler and why ("the
  three-way branch collapses to one call because X").
- **Where** — file:line.
- **Shape** — the catalog name plus the mechanical fix type.
- **Evidence** — the citations that survived Step 6; before/after structural
  counts where they help (max nesting 4→2, params 5→3), never composite
  scores.
- **Impact** — which cost it removes: change amplification, cognitive load,
  or obscured information. Claim comprehension cost, never defect or
  maintenance economics — those don't follow from shape alone.
- **Cleaner shape** — an edit recipe in small behavior-preserving steps;
  compound multi-file restructures get staged or demoted to follow-up.
- **Behavior preservation** — every requirement the shape touches; the test
  coverage status; if uncovered, the test that would make the edit safe.
- **Severity × disposition** — issue / suggestion / nit, crossed with:
  before merge / fine as a follow-up PR / question for the author.
  Signature- and hierarchy-crossing recommendations carry the highest
  regression risk — weight them down.

Order the report: findings in this change, then pre-existing complexity the
diff touches (labeled as such, never mixed in), then open questions. Group
findings that share one root cause into a single entry. Report at most three
nits and summarize the rest as a count. Keep recommendations proportional to
an in-review change — broad redesign only when a wrong abstraction boundary
is itself the direct cause. Skip polish on code that is feature-flagged,
experimental, or slated for deletion; suppress praise notes, out-of-diff
opportunities, linter territory, and questions that only ask for
explanation. Do not offer to apply the findings; the report is the whole
product.

A worked example of one finding:

> **Title:** `use_new_path` is dead weight — every caller passes `true`, so
> the old arm never runs.
> **Where:** `src/export.py:41` (parameter), `src/export.py:58-71` (old
> arm); call sites `src/cli.py:88`, `src/batch.py:130`,
> `tests/test_export.py:19,44`.
> **Shape:** constant-threaded flag or parameter → remove the parameter,
> delete the dead arm.
> **Evidence:** caller enumeration — grep finds exactly four call sites,
> each passing `use_new_path=True`; the flag arrived in commit 3 of this
> branch to keep the legacy arm alive during development, and commit 6
> moved the last caller off it.
> **Impact:** cognitive load — every reader of `export()` must understand a
> branch that cannot execute.
> **Cleaner shape:** delete the parameter and the `else` arm; no other
> signature change.
> **Behavior preservation:** the surviving arm is the one every caller
> already exercises; `tests/test_export.py` covers it directly.
> **Severity × disposition:** suggestion / before merge.
