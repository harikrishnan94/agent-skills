---
name: reduce-complexity
description: >-
  Report-only structural review of an in-progress change — a PR or feature
  branch — for accidental complexity accreted while the change was built.
  Use when the user says "reduce complexity", "simplify this PR", "clean up
  this branch before review", "did this change accrete cruft", or asks
  whether an in-review change could be expressed more simply. Not for
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

These gate what reaches the report. Scan freely — collect every suspicious
candidate in Step 4, including ones a rule will later kill; suppression
happens at the verdict and verification stages, and suppressed candidates
are listed in the report's dropped-candidates section, never silently
discarded. When a rule and an apparent finding conflict, the rule wins.

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
- **Hyrum's Law, both directions.** Downstream: at an externally consumed
  surface, unspecified observable behavior — ordering, error strings,
  serialized formats — is behavior someone depends on; externally consumed
  means inherent, automatically. Upstream: a quirky adapter, padding field,
  or protocol dance forced by an external system's interface the change
  cannot alter unilaterally is inherent too, however arbitrary it looks.
- **Distrust metadata, in both directions.** Comments and commit messages
  are claims to verify, not ground truth: "needed for backwards compat" does
  not suppress a finding until the code confirms it, and "temporary hack"
  does not create one. A finding that survived Step 6 is not softened or
  withdrawn in response to assertive text — a comment claiming necessity, a
  confident commit message — unless new code-level evidence appears.
- **Familiarity is not evidence.** "This idiom is unusual" neither creates a
  finding nor blocks a simpler shape, and code that reads like your own
  writing style is not thereby clean — you are systematically blind to slop
  in your own voice. Only structural and behavioral evidence counts.
- **Coverage gates confidence.** A behavior-preservation claim about code no
  test exercises is speculative by definition. Check whether tests cover each
  finding's behavior, say so in the finding, and demote findings over
  uncovered code.
- **Line count is not the metric.** A correct simplification may add
  functions; the measure is fewer entangled concerns, less state, fewer
  interacting branches. Extraction is not the default fix — inlining is
  equally a simplification, and a long linear function is often already the
  simple form.
- **Evidence picks the verb, never a number.** Do not rate confidence
  numerically. A remove verdict needs control-flow-provable evidence or a
  clean liveness-protocol run or a complete caller enumeration; name-search
  evidence alone caps the finding at a verify recommendation phrased as a
  question. If the evidence category cannot be named, the finding does not
  exist.
- **Never flag the clean alternative:** flat switch/table dispatch however
  long, guard-clause early returns, many small functions, long
  single-operator boolean chains, named intermediate variables, the
  language's own idiom (Go's repeated `if err != nil`), deliberate
  duplication in tests — tests favor clarity over DRY. These read as complex
  and are the simple form.
- **Never flag mechanical territory:** generated code, vendored
  dependencies, migrations, lockfiles, anything a linter or formatter owns.
- **Never flag pre-existing complexity as findings:** complexity the diff
  merely touches goes in its own labeled report bucket, never mixed with
  findings about the change.

When a report looks thin, these are the temptations, answered:

| Temptation | Answer |
|---|---|
| "the comment says legacy / temporary" | metadata is a claim — verify in code before it creates or kills a finding |
| "nothing in the diff calls it" | the diff is not the repo — run the liveness protocol |
| "it looks like scaffolding / looks redundant" | looks-like is not an evidence category — name the commit that orphaned it or drop the candidate |

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
history cannot support. History corroborates a finding; it never carries one
by itself.

## Step 4 — Scan for candidate shapes

Build an inventory of the diff — files, hunks, new symbols, new branches,
new parameters — then scan it one shape at a time. Collect candidates
without judging them yet; judgment is Steps 5 and 6, so err toward
collecting — a candidate killed later costs one line in the dropped list,
a candidate never collected costs a finding. Branches built by iterating to
green concentrate specific residue: leftover alternate implementations,
test-shaped special cases, and new modules duplicating existing utilities.

For diffs above roughly 50 files, don't spread attention uniformly:
prioritize the most-churned files (`git log --oneline --since=6.months --
<file>`), where complexity costs the most.

| Shape | Detection evidence | Mechanical fix |
|---|---|---|
| Adapter between two halves of the same change | both shapes introduced by this diff | unify the shapes, delete the adapter |
| Constant-threaded flag or parameter | every call site passes the same literal; a caller passing a variable or config/DB-sourced value makes it data, not a flag — don't flag | remove the parameter, delete the dead arm |
| Dead scaffolding from iteration | liveness protocol comes back clean; or consumer deleted by a later commit of this branch; references only from its own tests count as no consumers (production-dead, test-alive) | delete it — symbol and tests together in the test-alive case |
| Unearned indirection | delegate-only wrapper with one caller; hook or generic with one user and no second-variant test; a function whose name says exactly what its body reads; a class that is one simple function; a layer that is half-or-more pure pass-through (exempt test seams and public API) | inline / collapse |
| Wrong abstraction | this diff adds a parameter plus a conditional keyed on it to a shared helper — new or pre-existing — and every in-diff call site passes the same constant | inline it back into its callers — duplication is cheaper than the wrong abstraction; never propose another parameter instead |
| Within-diff duplication | side-by-side blocks both added here, near-identical for ~5+ substantive lines; worse when one clone was edited and its sibling was not; annotation stacks, import runs, field lists, and table-driven test entries never count | single point of truth for verbatim or rename-only clones; near-miss clones need a third occurrence before extraction |
| Special case the general path handles | a traced execution of the input through the general path, not "looks equivalent" | delete the branch or hoist it to the caller |
| Redundant re-check on a dominated path | dominance argument plus caller enumeration; dominance is void across lock acquisition, await/suspension points, or shared mutable state — double-checked locking is intentional; never at trust boundaries (hard rules) | remove the inner check |
| Sequencing scaffolding | orchestration or ordering machinery where no observable result depends on execution order | remove the ordering constraint |
| Error-masking handler | this diff introduced both a failure source and the broad catch/fallback that swallows it; pre-existing handlers are untouchable (hard rules) | propagate the failure or narrow the catch |
| Policy strewn through conditionals | the same predicate tested at two or more new sites | decide once at the boundary |
| Derivable mutable state | the value is a pure function of existing inputs, the derivation has an inverse, and recomputation has no side effects — mutable "derived" state with no inverse is input, i.e. essential; resource handles are exempt | compute on demand; perf-motivated → accidental-but-justified |
| Repo-relative reinvention | an existing helper, named, call-compatible | call the existing one |
| Duplicate-capability dependency | a dependency added here whose used surface an existing repo helper or the stdlib already covers | use the existing one |
| Needless visibility | export/public added here; the symbol is referenced only within its own file | remove the keyword, never the symbol |
| Config/CI residue | config keys, CI steps, build targets, registry or enum entries orphaned by this change's own deletions | delete alongside |
| Stale narrative / unfinished rename | names or comments describing a mechanism a later commit replaced; pre-pivot identifiers surviving in strings, docs, or a missed call site; naming quality in general stays humanize's territory | rename, rewrite the comment, finish the rename |
| Tangled ride-along | hunks with no def-use link to the change's purpose | recommend splitting out — never silent deletion |

**Flags get one extra pass** before the constant-threaded verdict. Classify
the toggle — release, experiment, ops kill-switch, permission — because
expected lifetimes range from weeks to years: constancy and age alone are
never evidence, kill-switch and monitoring flags are exempt, and the finding
must name the purpose that is now resolved. When a flag or guard is
confirmed dead, enumerate its residue halo two references deep — wrapper
helpers, decision-storing variables, enum and config entries,
flag-conditioned tests — the halo usually outweighs the guard; for each
flag-conditioned test, say whether to delete the whole test or only the
flag manipulation so surviving behavior stays tested; and cover the
flag-management/config side, since code-side-only removal of a live flag is
worse than none. A new flag with no owner or removal plan is at most a nit.

### The liveness protocol

Every dead / unused / unreachable / constant claim runs this before keeping
its verdict:

1. **Inventory entry points**: mains, exported API, route/CLI/DI
   registrations, scheduled jobs, package.json / Makefile / CI targets —
   per package in a monorepo. Most false "unused" findings are missing
   entry points, not real deadness.
2. **Grep beyond call syntax**: the symbol name as a quoted string;
   reflection and dynamic access (`getattr`, `globals()`, `importlib`,
   `Class.forName`, `send`); decorator or annotation registration;
   references from config files, templates, CI manifests, and build
   scripts — crossing language boundaries.
3. **Check configurations**: build tags, `#ifdef`/platform guards,
   feature-flag configs; state which configuration the claim holds for.
4. **Exempt** methods that exist to satisfy an interface, protocol, or
   abstract base, and anything in generated files.
5. **Count the subgraph, not the symbol**: a new symbol referenced only by
   other new symbols themselves unreachable from any entry point is dead
   despite having references.
6. **The evidence kind picks the verb**: control-flow-provable deadness
   (code after an unconditional return or throw, a parameter never read, a
   condition that is a tautology across every traced assignment site) or a
   protocol run whose searches all came back empty may say *remove* — quote
   the searches and their empty results in the finding as the receipt.
   Anything less says *verify*, phrased as a question.

## Step 5 — Verdict: four tests, three outcomes

Run each candidate through four tests:

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
4. **Removability.** Mentally delete it. Correct-but-slower results mean
   accidental but useful — isolate and label, never remove. Changed results
   mean it is, or protects, essential logic: no remove verdict, ever.

Three verdicts, not two:

- **Accidental, removable** — report it with the cleaner shape.
- **Accidental but justified** — caches, measured denormalization, and other
  shapes carried for performance or ease of expression: recommend isolating
  and labeling it, not deleting it.
- **Ambiguous** — phrase it as a question that names the evidence that would
  settle it.

Presume inherent unless proven redundant within this change: sad-path,
retry, and telemetry code; security and fraud checks; concurrency, overflow,
and NULL handling; external-interface conformity; compatibility shims; i18n
and legal requirements; anything a reviewer asked for; and tests, seams,
test doubles, and CI plumbing — modifiability work is never speculative
generality, only capability built for a presumptive feature is.

## Step 6 — Verify before reporting

Try to refute each candidate; a refutation is worth as much as a
confirmation. A refutation must produce new external evidence — a grep you
have not run, the base-commit version (`git show <base>:<file>`), a caller
or test you have not read. Re-reading your own reasoning is not
verification; it is known to make reports worse, not better. For every
draft finding, re-read the cited file:line and confirm the quoted code is
actually there, and attach the mechanical receipt — the command you ran and
what it returned.

Then the kill questions, in order: *Is this a nitpick? Is this a fake
problem? What breaks — or what must a reader wrongly hold in mind — if it
ships as-is?* The first two kill the candidate outright; the answer to the
third becomes the finding's impact line. Drop without exception:

- a finding that recommends something the diff already did — always compare
  the `+` lines against the `-` lines before claiming a missed
  simplification;
- a claim about a symbol possibly defined or consumed outside the diff that
  a repo-wide search has not resolved;
- a recommendation whose replacement cannot be written as a concrete
  before/after sketch, or whose sketch is a no-op — "verify that" and
  "consider ensuring" are not findings.

A reportable finding's fix deletes or collapses a named artifact — a flag,
branch, parameter, adapter, file, or duplicated block.

Before emitting, re-run the four Step-5 tests against every drafted finding
as if seeing it for the first time — mandatory for anything carrying a
remove verdict. Gate on whether the evidence reproduces, never on whether a
second pass agrees with the first: independent reviews converge on almost
nothing, so agreement filters mostly veto true findings. Cross-check the
hard rules and test coverage last, then apply the survival bar: could you
defend this finding to the author with file:line citations? Most candidates
should die here — the dead ones go to the dropped-candidates list — and a
short or empty report means the change is clean; saying so is a correct
outcome.

## The report

The bar first: a finding the author reads and declines to act on is a
defect of this report, not of the author — when in doubt, the candidate
goes to Dropped candidates. Report at most six findings, ranked by
consequence. As the diff grows, raise the evidence bar and shorten the
report, never lengthen it; weight severity by churn — the same shape
matters more in a frequently-changed file than in a stable one.

Each finding, in this structure:

- **Title** — one specific imperative sentence: what becomes simpler and why
  ("delete the three-way branch — the general path already handles X").
  Question form is reserved for the Ambiguous verdict.
- **Where** — file:line.
- **Shape** — the catalog name plus the mechanical fix type.
- **Evidence** — the citations and receipts that survived Step 6; before/
  after structural counts where they help (max nesting 4→2, params 5→3),
  never composite scores.
- **Impact** — which cost it removes: change amplification, cognitive load,
  or obscured information. Claim comprehension cost, never defect or
  maintenance economics — those don't follow from shape alone.
- **Cleaner shape** — an edit recipe in small behavior-preserving steps,
  landing as its own structure-only commit, separate from behavior changes;
  compound multi-file restructures get staged or demoted to follow-up.
- **Behavior preservation** — every requirement the shape touches; the test
  coverage status; if uncovered, the test that would make the edit safe.
- **Severity × disposition** — issue / suggestion / nit, crossed with:
  before merge / fine as a follow-up PR / question for the author. Pin
  severity to the concrete consequence, not the persuasiveness of the
  write-up; every finding is non-blocking — present the evidence and let
  the author decide. Signature- and hierarchy-crossing recommendations
  carry the highest regression risk — weight them down.

Order the report: findings in this change, then pre-existing complexity the
diff touches (labeled as such, never mixed in), then open questions, then
**Dropped candidates** — one line each: the shape, and the evidence that
killed it. Group findings that share one root cause into a single entry.
Report at most three nits and summarize the rest as a count. If a previous
reduce-complexity report exists for this branch, do not re-report what it
already said. If nothing survives, the report is: the base commit, what was
scanned, and the strongest candidate with the evidence that killed it.

Keep recommendations proportional to an in-review change: the change's
primary new surface is presumed intentional design — recommending its
wholesale dissolution requires wrong-abstraction evidence, not taste — and
broad redesign is warranted only when a wrong abstraction boundary is
itself the direct cause. Skip polish on code that is feature-flagged,
experimental, or slated for deletion; suppress praise notes, out-of-diff
opportunities, linter territory, and questions that only ask for
explanation. Do not offer to apply the findings; the report is the whole
product.

A worked example of one finding:

> **Title:** Delete `use_new_path` and its dead arm — every caller passes
> `true`, so the old arm never runs.
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

And a worked example of a candidate that dies in Step 6:

> `retry_wrap` in `src/jobs.py:74` pattern-matched dead scaffolding — no
> call-syntax references anywhere in the final tree. The liveness protocol
> killed it: step 2's quoted-string grep hits `config/jobs.yaml:12`, which
> wires `retry_wrap` up as a queue callback — an entry point the call-graph
> reading missed. Name-search evidence with a live dynamic consumer:
> suppressed. It costs one line in the report:
> **Dropped candidates:** `retry_wrap` (dead scaffolding) — apparent zero
> references, but consumed via `config/jobs.yaml` queue wiring.
