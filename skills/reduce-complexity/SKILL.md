---
name: reduce-complexity
description: >-
  Structural review of an in-progress change — a PR, a feature branch, or a
  commit range — for complexity it does not need. It first fixes what the
  change is for (from the user, the PR, the issue, the commits and the
  tests), then looks for a way to reach the same intent that is simpler,
  more boring and shorter, and for residue left while the change was built.
  Told to "reduce complexity", "simplify this PR", or "clean up this branch
  before review", it applies the proven-safe simplifications by default and
  reports what changed; asked a question — "did this change accrete cruft",
  is there a simpler way to do this — or told "report only", it reviews
  without editing. Not for line-level style cleanup (humanize) or
  bug-hunting (code review).
---

# Reduce complexity: reach the same intent with less

You are reviewing an in-progress change to find where it could be expressed
more simply. There are two ways that happens, and you look for both:

- **The approach.** The change takes the long way while a shorter path
  exists: something the repo, its libraries or its platform already
  provides, or a fix where the problem starts instead of at every consumer
  (Step 3's moves).
- **The residue.** Fixes that got an incrementally built change working were
  never folded back into the design: dead arms, adapters between its two
  halves, leftover scaffolding.

Four properties govern everything below:

- **Intent first.** Every verdict is relative to a written intent record
  (Step 2). A construct is needless only against a requirement list, and a
  simpler approach is simpler only if it meets every line of it.
- **Fix by default, evidence-gated.** An imperative invocation applies what
  clears Step 8's gate; a question or an explicit "report only" makes the
  run read-only (Step 8 tells them apart): the user's tree does not change,
  though a scratch-copy prototype (Step 7) is still allowed unless the
  caller or the user forbids running code.
- **Base-commit-scoped.** Findings and applied edits live in the diff
  against an explicitly established base commit (Step 1), not the codebase
  at large, except the few forced lines Step 8 bounds and an approach
  finding's fix location where the problem starts (the loader, the schema).
- **Structural.** This skill judges how the change is put together; line-
  and function-level tells (comment noise, defensive theater, naming) are
  `humanize`'s, and bug-hunting is code-review tooling's.

## Four words, defined

The goal is a version of the change that is simple, boring, short and, when
the problem allows, elegant. Each word has a test, and its counts go into
the Step 3 ledger. A claim that cannot pass its word's test is taste, and
taste is not a finding.

- **Simple** — fewer concerns braided together, less new state, and fewer
  obligations on callers and modifiers, for the same intent. Two concerns
  are braided when they share mutable state or control flow, or when
  understanding one new unit means reading another. New state is a value
  that outlives one call or is shared between units; a local variable is not
  state. An obligation is an ordering constraint, precondition or implicit
  invariant a caller or modifier must respect: code that is easy to misuse
  is complex, however short. Test: under the diff and under the alternative,
  count braids, new state and modes, interacting branches, caller
  obligations, and the cases a reviewer must check. The alternative is
  simpler when it is lower on at least one of these counts and higher on
  none, even with more units. Not simple: fewer lines, fewer functions,
  something that feels familiar, or complexity moved to callers, config, or
  a later PR.
- **Boring** — the lowest rung of this ladder that does the job. Lowest is
  calling something the repo already has that does the job: a helper, a
  module, a constraint. Then a language construct; the standard library; a
  dependency or platform the repo already runs on (its database, its
  framework); a pattern the repo already uses; then new code, which includes
  the diff's own new helpers and abstractions; and last a new dependency or
  paradigm, or reflection, metaprogramming, code generation or a new
  concurrency primitive, whatever library it comes from. Test: every
  mechanism carries two receipts. Prevalence: a grep count with two or three
  file:line uses, the manifest entry, or the stdlib or platform docs. Known
  failure modes: an existing test or error-handling path for that mechanism
  in this repo, or the docs' account of how it fails. Prevalence without the
  second receipt is "used, not boring", and no receipt at all is "unknown";
  either way the mechanism gets no boring credit and sits on the new-code
  rung. Not boring: what you happen to know, or a common repo pattern that
  is itself the complexity.
- **Short** — the fewest elements a reader must learn. Test: count names
  visible outside their unit (exported symbols, parameters, types), files,
  dependencies, public surface and patched call sites. Branches belong to
  Simple; local variables count nowhere. Never characters or lines: an
  alternative that packs more into each line, nests deeper, or inlines a
  named intermediate or small function whose body survives at the call site
  is not shorter. Inlining that also deletes work — a second pass, a
  duplicated loop, a fold-after step the first loop can do — is shorter, and
  simpler too. A smaller diff may be noted under switching cost, never as
  the reason for a verdict.
- **Elegant** — a restatement of the problem under which a special case or
  an error path disappears, so the argument that the code is correct gets
  shorter: an error defined out of existence, or a special case the general
  path absorbs (a sentinel node that makes deleting the list head the
  ordinary case). Test: write the list of cases a reviewer must check under
  each shape and count them; the idiom must have precedent, either a repo
  use (file:line) or a language-spec or stdlib-docs page that shows it. Not
  elegant: clever, novel, dense, reflection or metaprogramming.

When they conflict, the order is fixed. First, the full intent is met and
behavior is preserved; nothing trades against that. Then simple, then
boring, then short. An alternative wins on a word when it is lower on at
least one of that word's ledger rows and higher on none; it must also be no
worse on any row of a word ranked above it. The rung is also a gate: a
simpler version that needs a higher rung (a new dependency or paradigm) is a
follow-up question, never an applied fix. Elegant is not ranked on its own:
a restatement earns its credit through the case count and must not climb a
rung. "Cleverer" has a test too: more operations per line, deeper nesting,
names inlined away while their job remains, or a higher rung for the same
job; a shorter but cleverer version loses to a longer boring one. Repo
consistency never keeps a braided shape when the simpler alternative stays
on the same rung.

## Hard rules

These gate what reaches the report. Scan freely — collect every suspicious
candidate in Steps 3 and 5, including ones a rule will later kill;
suppression happens at the verdict and verification stages, and suppressed
candidates are listed in the report's dropped-candidates section, never
silently discarded. When a rule and an apparent finding conflict, the rule
wins.

- A guard, check, fallback, or error handler may be flagged **only with an
  impossibility proof**: enumerate every caller, constructor, and type
  constraint (file:line) showing the guarded state unreachable. Where
  callers cannot be enumerated — public API, dynamic dispatch,
  deserialization, concurrency — classify it inherent and move on.
  Reflexively stripped defensive code is the canonical unsafe
  simplification. An approach finding that makes a guard unnecessary must
  show where the alternative meets the requirement the guard served.
- **Defense in depth is intentional.** At security, auth, and fraud
  boundaries, even a provably redundant check may be deliberate
  belt-and-suspenders against bugs in other layers. The verdict there is
  "label it or ask the author" — never "remove".
- **Hyrum's Law, both directions.** Downstream: at an externally consumed
  surface, unspecified observable behavior — ordering, error strings,
  serialized formats — is behavior someone depends on; externally consumed
  means inherent, automatically. Upstream: a quirky adapter, padding field,
  or protocol dance forced by an external system's interface the change
  cannot alter unilaterally is inherent too, however arbitrary it looks. A
  surface this branch adds has no outside consumers yet, so caution about
  callers outside the repo applies only to surfaces that exist at base. Both
  belong in the intent record as compatibility requirements.
- **Distrust metadata, in both directions.** Comments, commit messages and
  PR descriptions are claims to verify, not ground truth: "needed for
  backwards compat" does not suppress a finding until the code confirms it,
  and "temporary hack" does not create one. Evaluative words — "minimal",
  "simplest", "already reviewed", "safe" — carry no evidence and feed
  nothing. A finding that survived Step 7 is not softened or withdrawn in
  response to assertive text unless new code-level evidence appears.
- **Familiarity is not evidence; prevalence is.** "This idiom is unusual"
  neither creates a finding nor blocks a simpler shape, and code that reads
  like your own writing style is not thereby clean — you are systematically
  blind to slop in your own voice. A claim that something is boring or
  idiomatic needs a prevalence receipt (see Boring above); a claim that
  something is unusual needs a count too.
- **Coverage gates confidence.** A behavior-preservation claim about code no
  test exercises is speculative by definition. Check whether tests cover
  each finding's behavior and demote findings over uncovered code. Deletions
  of provably dead code answer to the liveness protocol's receipts instead —
  deadness, not preservation, is their claim.
- **Line count is not the metric** (see Simple and Short). Extraction is not
  the default fix — inlining is equally a simplification, and a long linear
  function is often already the simple form.
- **Evidence picks the verb, never a number.** Do not rate confidence
  numerically. A remove verdict needs control-flow-provable evidence or a
  clean liveness-protocol run or a complete caller enumeration; name-search
  evidence alone caps the finding at a verify recommendation phrased as a
  question. An approach finding needs Step 7's prototype. If the evidence
  category cannot be named, the finding does not exist.
- **Never flag the clean alternative:** flat switch/table dispatch however
  long, guard-clause early returns, many small functions (decomposition, not
  a helper that adds a pass, a mode or state), long single-operator boolean
  chains, named intermediate variables, the language's own idiom (Go's
  repeated `if err != nil`), deliberate duplication in tests — tests favor
  clarity over DRY. These read as complex and are the simple form.
- **Never flag mechanical territory:** generated code, vendored
  dependencies, migrations, lockfiles, anything a linter or formatter owns.
- **Never flag pre-existing complexity as findings:** complexity the diff
  merely touches goes in its own labeled report bucket, never mixed with
  findings about the change.
- **Never judge the goal itself.** Whether the intent is worth having is the
  author's and the reviewers' call. At most it becomes an open question.

When a report looks thin, or too confident, these are the temptations,
answered:

| Temptation | Answer |
|---|---|
| "the comment says legacy / temporary" | metadata is a claim — verify in code before it creates or kills a finding |
| "nothing in the diff calls it" | the diff is not the repo — run the liveness protocol |
| "it looks like scaffolding / looks redundant" | looks-like is not an evidence category — name the commit that orphaned it or drop the candidate |
| "I would have designed it differently" | only a ledger that wins for the same intent counts (Step 7) |
| "the alternative is more elegant" | name the counted axis, or drop it |
| "the two versions are equivalent" | only an executed prototype shows that; reading both is not evidence |
| "the simpler version just skips the error / compat path" | the coverage map says no — that is a smaller intent, not a simpler change |
| "the PR says this is the minimal fix" | evaluative metadata — ignore it |

## Step 1 — Establish the change set

Fix the scope first: the diff between the current branch and a base commit.

1. **Given range.** When the caller names a commit range (`<base>..<head>`,
   as `review-pr` does), that is the scope. Do not check anything out. Read
   with `git show <rev>:<file>`, search with `git grep <pattern> <head>`,
   and pass `<base>` and `<head>` to every `git diff` and `git log` (the
   Step 2 file list, the Step 4 history, the Step 5 churn count). Never use
   the working tree or the checked-out `HEAD`, which may hold an unrelated
   branch.
2. **A fix's own hunks.** When the caller scopes you to its own uncommitted
   fix (as `watch-pr` does), the scope is those working-tree hunks against
   `HEAD`. They are the caller's edits, not the author's, so Step 8's
   dirty-file rule does not block them. Edit only inside them; what you
   notice in the author's surrounding code goes in the pre-existing bucket,
   labeled as the author's code, and is never edited.
3. **PR branch.** Find the current branch (`git rev-parse --abbrev-ref
   HEAD`) and check for an associated pull request (`gh pr view`, or the
   host's tooling). If one exists, the base commit is `git merge-base HEAD
   <pr-base-branch>`.
4. **Non-PR branch.** Derive the base: the upstream merge-base (`git
   merge-base HEAD @{upstream}`) if an upstream is set; else the merge-base
   with whichever integration branch exists (`main`, `master`, `develop`,
   `trunk`); else the divergence point from `git log --first-parent` and the
   reflog. When the user named a base or the derivation is unambiguous,
   state the base commit and the assumption and proceed; when candidates
   genuinely compete, ask — the entire review scope depends on it.

The changed lines are the primary scope. Read surrounding code, call sites,
and tests as needed — a shape that looks redundant in the diff may be
load-bearing once you see how it is used.

## Step 2 — Establish the intent

Write down what the change has to do before judging how it does it. Read the
sources in this order. When sources disagree on scope — the goal and the
non-goals — the earlier one wins. On behavior, an executed test outranks
prose; record any conflict between the two under Assumptions and handle it
as When to ask says.

1. **The user's statement** in this invocation. It sets the scope, but hunks
   it does not explain are still reviewed and reported.
2. **The linked issue or ticket**, as amended by decisions accepted later in
   the review thread.
3. **The PR title and description.** Descriptions go stale as a change is
   reworked.
4. **The PR's review threads**, human and bot, whenever a PR exists. An
   accepted ask becomes a Constraint line — a hard one, however awkward the
   shape it forces — and outranks the issue and the description where they
   disagree, because descriptions are rarely updated after review. The
   absence of a comment is not evidence that a shape is unjustified: most
   review-round reshaping never gets one. This read does not count against
   the handful of reads below.
5. **Commit messages** — good for what changed, weak for why. A message that
   quotes or restates the issue counts as the issue when the issue itself is
   out of reach.
6. **The tests the change adds or edits.** A test that fails at base and
   passes at head pins the intended behavior change; existing tests that
   pass at both pin compatibility. To tell which, when running code is
   allowed, fill a second scratch directory (Step 7) with `git archive
   <base>`, copy in the test files the change adds or edits from `<head>`,
   and run them there. Otherwise mark the line "unverified here": an
   unverified test outranks no prose, so a conflict with it is recorded and
   asked like any other. A change described as a refactor whose tests fail
   at base is a behavior change. Treat only behavior-level assertions as
   requirements; a test that checks an internal helper pins the author's
   mechanism, not the intent.
7. **The observable behavior change** you can read from the diff. Always
   label it inferred.

Bound this to a handful of reads, then write the **intent record**, in at
most about ten lines:

- **Goal** — one sentence: the problem and its user-visible effect, stated
  as behavior, with no symbol names from the diff.
- **Requirements** R1..Rn — each an input and the expected behavior, sad
  paths and data already in the field included, each with its source (user /
  issue / PR / commit / test / inferred).
- **Compatibility** — what must keep working: pass-at-both tests, externally
  consumed surfaces, stored data and formats.
- **Non-goals** — things that could reasonably be in scope but are not.
- **Constraints** — accepted review asks, performance budgets with numbers,
  platform, rollout, and alternatives the author already ruled out, with
  their reason.
- **Assumptions** — every reading you chose where sources were silent or
  disagreed, with the reading you rejected.

Keep the author's solution choices out of the requirements: "adds a
`retry_after` parameter to the client" is a mechanism; "a 429 response is
retried after the delay the server asked for" is a requirement.

Then check each claim against the diff's file list and hunk headers (`git
diff --stat <base> <head>` and the `@@` lines of `git diff -U0 <base>
<head>`, not the hunk bodies). A claimed change with no matching hunk is a
phantom and goes to Open questions. The other direction — a hunk no
requirement explains — waits for Step 3, after the sketch. If the goal needs
two unrelated sentences, the change carries two intents: report the split
and judge each part on its own, never one alternative across both.

**When to ask.** If two readings of the intent, or a conflict between a
claimed source and a test, would change any intent-dependent verdict — an
approach finding, "not needed", a ride-along, a removed special case — and
an attended user can answer, ask once, before any edit, at most three
questions, each as a concrete behavior example ("after this change, an empty
upload returns 200 with no rows instead of a 400 — intended?"), never a fact
the code can answer. In an unattended or report-only run, never block:
proceed on the most defensible reading, record it under Assumptions, and
phrase every finding that depends on it as a question.

An approach finding needs at least one intent source independent of the diff
itself — the user, the issue, the description, a commit message that states
the problem, or a fail-at-base test. Intent inferred only from the diff
matches the diff by construction, and a simpler approach judged against it
is taste.

When the scope is a fix's own hunks (`watch-pr`), the intent is that fix's
purpose — the failing check or the review comment it answers — and Steps 3
and 5 judge only those hunks.

## Step 3 — Sketch the boring solution first

Before reading the diff's production code closely, design the change
yourself from the intent record and the base-commit code (`git show
<base>:<file>`). The author's shape anchors whoever reads it first, and an
alternative found after studying the diff tends to be the diff with small
edits. Write the sketch down, in your working notes, before you compare.

Search for the boring path move by move, at named places — never with an
open-ended "is there a simpler way":

| Move | Where to look | Evidence it applies |
|---|---|---|
| Something already provides it | the stdlib; the platform, database or framework the repo already runs on; dependencies in the manifest; repo helpers near the change | the API named, with the repo's existing uses of it (file:line) |
| Fix it where the problem starts | the loader, parser, schema, constructor or boundary that every consumer reads through | one place that every affected consumer passes through, shown by caller enumeration |
| Let the data layer enforce it | constraints, unique indexes, transactions, defaults, types | the rule is a property of the data, and the store supports it |
| Delete or reuse instead of add | the requirement list | no requirement names the new construct, or an existing one already serves it |
| Data instead of code | parallel branches this diff adds that repeat the same logic and differ only in constants | a table holds the variation; a flat switch is already data-shaped, never convert one |
| Define the error out of existence | the interface where the special case or error arises | a restated normal case covers the special one |
| Make the change easy first | base-commit structure the change keeps working around | a behavior-neutral preparatory refactor, then a small change |
| Don't build it yet | generality, options, hooks | no second real use and no requirement asks for it |

Climb the boring ladder one rung at a time, starting with nothing new. When
no move fits, also sketch one radically different approach (design it
twice): another decomposition, or meeting the requirements with no new
component at all. It answers to the same ledger and the same bar.

Fill in the sketch's column of the **ledger** now and the diff's column
while you reconcile below, one row per counted element of the four words.
Simple: braids, new state and modes, interacting branches, caller
obligations, cases a reviewer must check. Boring: the rung of each mechanism
and its receipts. Short: externally visible names, files, dependencies,
public surface, patched call sites. These counts are what the four words
mean in a finding. A shape on the never-flag list never counts against
either column, in any row: flat switch arms and guard-clause returns are not
interacting branches, and named intermediates and small functions are not
extra names.

Then reconcile. Read the diff closely and compare it with the sketch. A
significant hunk no requirement explains is scope creep or a tangled
ride-along candidate. Before an approach candidate leaves this step, list
the callers and uses (file:line) of every symbol the diff adds or changes: a
caller the sketch did not account for is a missed requirement.

- A construct the diff has and the sketch lacks is either a requirement the
  sketch missed — add it to the intent record with its evidence (the test,
  caller or stored data that needs it) — or a candidate for Step 5.
- Where the sketch wins on a word (lower on at least one of its rows, higher
  on none), is no worse on any row of a higher-ranked word, and meets every
  requirement, it becomes an **approach candidate** for Step 7.
- Where the sketch wins only by dropping a requirement, it dies here; list
  it in Dropped candidates with the requirement it dropped.

Most changes have no approach candidate. "No simpler approach found, and
here is what was checked" is a correct outcome, and the default for a small
diff.

## Step 4 — Read the branch history as evidence

The verdict is always on the final state, but the commit sequence is
evidence you have nowhere else: a helper, parameter, or branch introduced at
commit k whose reason had disappeared by the final commit is the accretion
signature, and hunks reworked across three or more commits or review rounds
are where it concentrates — scan those first. A branch whose commits each
patch one more consumer of the same problem is the signature of a fix at the
wrong layer.

Check that the history is real before reading it: squashing and rebasing
make commit order no longer construction order. A single-commit branch or
freshly rebased history means the archaeology is unavailable — rely on
final-state evidence alone, and never narrate a construction story the
history cannot support. History corroborates a finding; it never carries one
by itself.

## Step 5 — Scan for candidate shapes

Build an inventory of the diff — files, hunks, new symbols, new branches,
new parameters — then scan it one shape at a time, collecting without
judging (Hard rules: scan freely; judgment is Steps 6 and 7). Branches built
by iterating to green concentrate specific residue: leftover alternate
implementations, test-shaped special cases, and new modules duplicating
existing utilities.

Scan the code an approach candidate would replace too; Step 8 says why.

For diffs above roughly 50 files, don't spread attention uniformly:
prioritize the most-churned files (`git log --oneline --since=6.months
<head> -- <file>`), where complexity costs the most.

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
| Tangled ride-along | hunks no requirement in the intent record explains | recommend splitting out — never silent deletion |

**Flags get one extra pass** before the constant-threaded verdict. Classify
the toggle — release, experiment, ops kill-switch, permission — because
expected lifetimes range from weeks to years: constancy and age alone are
never evidence, kill-switch and monitoring flags are exempt, and the finding
must name the purpose that is now resolved. When a flag or guard is
confirmed dead, enumerate its residue halo two references deep — wrapper
helpers, decision-storing variables, enum and config entries,
flag-conditioned tests — the halo usually outweighs the guard; for each
flag-conditioned test, say whether to delete the whole test or only the flag
manipulation so surviving behavior stays tested; and cover the
flag-management/config side, since code-side-only removal of a live flag is
worse than none. A new flag with no owner or removal plan is at most a nit.

### The liveness protocol

Every dead / unused / unreachable / constant claim runs this before keeping
its verdict:

1. **Inventory entry points**: mains, exported API, route/CLI/DI
   registrations, scheduled jobs, package.json / Makefile / CI targets — per
   package in a monorepo. Most false "unused" findings are missing entry
   points, not real deadness.
2. **Grep beyond call syntax**: the symbol name as a quoted string;
   reflection and dynamic access (`getattr`, `globals()`, `importlib`,
   `Class.forName`, `send`); decorator or annotation registration;
   references from config files, templates, CI manifests, and build scripts
   — crossing language boundaries.
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
   the searches and their empty results in the finding as the receipt;
   anything less says *verify* (Hard rules).

## Step 6 — Verdict: four tests, three outcomes

Run each candidate through four tests:

1. **Re-derivation.** If the author rewrote the change in one sitting from
   the intent record, would this construct exist? Constructs that only make
   sense given the order the branch was built are accidental by
   construction.
2. **Requirement.** Name the intent-record line the construct serves. A
   construct that serves only a non-goal is a candidate. If it serves no
   line, the verdict is "ask the author" — never "removable" — however the
   record was sourced: the record is short, and a shape can be the residue
   of two requirements interacting. Code the liveness protocol proves dead
   is outside this test: its claim is deadness, not a missing requirement,
   and the protocol's verb stands.
3. **Availability.** Accidental means avoidable with means already at hand.
   Name the means: the existing repo helper, the stdlib call, the platform
   feature, the established idiom — with its receipt.
4. **Removability.** Mentally delete it. Correct-but-slower results mean
   accidental but justified. Changed results mean it is, or protects,
   essential logic: no remove verdict, ever.

Three verdicts, not two:

- **Accidental, removable** — report it with the cleaner shape.
- **Accidental but justified** — caches, measured denormalization, and other
  shapes carried for performance or ease of expression: recommend isolating
  and labeling it, not deleting it.
- **Ambiguous** — phrase it as a conditional question that names the
  evidence that would settle it ("if nothing outside this repo imports `X`,
  delete it?").

Presume inherent unless proven redundant within this change: sad-path,
retry, and telemetry code; security and fraud checks; concurrency, overflow,
and NULL handling; external-interface conformity; compatibility shims; i18n
and legal requirements; anything a reviewer asked for; and tests, seams,
test doubles, and CI plumbing — modifiability work is never speculative
generality, only capability built for a presumptive feature is. An approach
candidate may still replace such code when it meets the same requirement
another way, except security, auth and fraud checks and shapes a reviewer
asked for, which it may only label or ask about.

## Step 7 — Verify before reporting

Try to refute each candidate; a refutation is worth as much as a
confirmation. A refutation must produce new external evidence — a grep you
have not run, the base-commit version (`git show <base>:<file>`), a caller
or test you have not read. Re-reading your own reasoning is not
verification; it is known to make reports worse, not better. For every draft
finding, re-read the cited file:line and confirm the quoted code is actually
there, and attach the mechanical receipt — the command you ran and what it
returned.

Then the kill questions, in order: *Is this a nitpick? Is this a fake
problem? Does the alternative remove the complexity or only move it — to
callers, config, a new dependency, a later PR? What breaks — or what must a
reader wrongly hold in mind — if it ships as-is?* The first three kill the
candidate outright (moving complexity into a deeper module whose interface
clearly shrinks is not "only moving it"); the answer to the fourth becomes
the finding's impact line. Drop without exception:

- a finding that recommends something the diff already did — always compare
  the `+` lines against the `-` lines before claiming a missed
  simplification;
- a claim about a symbol possibly defined or consumed outside the diff that
  a repo-wide search has not resolved;
- a recommendation whose replacement cannot be written as a concrete
  before/after sketch, or whose sketch is a no-op — "verify that" and
  "consider ensuring" are not findings;
- an approach the author already ruled out, unless you checked their stated
  reason in code and it does not hold; say what you checked.

A reportable finding's fix deletes, collapses, or rewrites a named artifact
— a flag, branch, parameter, adapter, file, duplicated block, or stale name
or comment — or, for an approach finding, replaces a named set of them with
a named existing means.

### The bar for an approach finding

An approach finding proposes reaching the intent another way. It is
report-only unless the user asks for that approach to be applied, and it
must carry all of these:

1. **Coverage map** — every requirement and compatibility line of the intent
   record, mapped to the place in the alternative that meets it. An unmapped
   line kills the finding or demotes it to a question.
2. **Sketch** — the alternative as code: the before/after of each place it
   changes, short enough to read in one pass.
3. **Reuse receipt** — the existing means it relies on, with file:line of
   its current uses in this repo, or the stdlib or platform docs for it. The
   sketch uses the mechanism the receipt cites, not a cousin of it.
4. **Ledger** — the Step 3 counts for the diff and for the alternative: the
   alternative wins on a word (lower on at least one of its rows, higher on
   none), is no larger on any row of a higher-ranked word, and is on the
   same or a lower ladder rung. "Equally valid" is taste: drop it.
5. **Prototype** — the alternative applied in a scratch copy outside the
   user's tree: a new directory under the session scratchpad or from `mktemp
   -d`, filled with `git archive <head> | tar -x -C <scratch>`. In a
   read-only run that is the only copy method; a `git worktree` added in an
   editing run is removed afterwards. In hunk mode the head is the working
   tree, which `git archive` does not see: copy its tracked and untracked,
   non-ignored files instead (`git ls-files -co --exclude-standard`). Run
   the change's own tests there first, and the full suite only if they pass.
   Tests that check a requirement must pass. A test that pins the replaced
   mechanism — calls a helper the alternative deletes, or builds a state the
   alternative makes impossible — is deleted when an existing test already
   checks the same requirement (name that test), and otherwise rewritten in
   the scratch copy to check it; a rewritten test must also pass against
   head and, when the original failed at base, fail at base too. The finding
   names each deleted or rewritten test. For each requirement the
   alternative meets in a different way, run at least one input through head
   and through the prototype and compare: claim only "same behavior on these
   inputs". Keep every line the move does not require; never special-case
   test inputs. If you cannot prototype here, or the caller forbids running
   code (`review-pr` does not build by default), the finding is a question
   that names the prototype that would settle it.
6. **Switching cost** — files and lines to rewrite, tests to change, data to
   migrate, and the risk. Weigh only cost from here on: the author's effort
   so far and the current code's presence are not evidence.
7. **Unless** — the fact that, if true, would make the diff's shape the
   right one: a caller outside the repo, stored data, a rollout step, a
   performance number. The author can then refute the finding in one line.

If the prototype shows the current diff wrong on some input — a race, a case
it misses — that is the alternative's strongest evidence: name the input.
Bug-hunting is still not this skill's job, so report it as part of the
finding, not as a separate bug.

Before emitting, re-run the four Step-6 tests against every drafted finding
as if seeing it for the first time — mandatory for anything carrying a
remove verdict. Gate on whether the evidence reproduces, never on whether a
second pass agrees with the first: independent reviews converge on almost
nothing, so agreement filters mostly veto true findings. Cross-check the
hard rules and test coverage last, then apply the survival bar: could you
defend this finding to the author with file:line citations? Most candidates
should die here, and a short or empty report means the change is clean;
saying so is a correct outcome.

## Step 8 — Apply what the evidence supports

Mode first. An imperative invocation — "reduce complexity", "simplify this
PR", "clean up this branch" — applies surviving findings before the report
is written. A question-phrased invocation ("did this change accrete cruft?")
or an explicit "just report" / "don't change anything" is a report-only run:
skip this step and, for questions, close the report by offering to apply.

Preflight, before the first edit:

- Run the repo's verification once on the untouched tree — the narrowest
  test selection exercising the diff plus the repo's standard quick gate
  (build, typecheck), extended to the full suite when any deletion-type
  finding is a candidate. This is the baseline: only failures new against it
  indict an edit. If verification cannot run in this environment (CI-only,
  missing services or secrets), the run demotes to report-only, findings
  marked unverifiable here.
- Record every edit so it can be undone exactly: snapshot the pre-edit state
  first (`git stash create`, noting the SHA without stashing, or a saved
  diff plus copies of the files in scratch). "Revert" below means
  inverse-applying the skill's own recorded edits — never `git restore` or
  `git checkout` against HEAD, which on a dirty tree destroy the author's
  uncommitted work.
- Never edit a file that already carries uncommitted author changes;
  findings touching one demote to report-only.

The gate, per finding — the verdict must be *accidental, removable*, and the
fix type picks its oracle:

- **Restructures** — inline, collapse, hoist, unify, dedup, decide-once:
  need the remove-verdict evidence bar (Hard rules; a traced execution and
  verbatim in-diff clone identity qualify as control-flow grade for their
  shapes) AND existing tests exercising the behavior the edit moves through.
- **Deletions of production-dead code** — dead scaffolding, dead arms,
  needless visibility, config residue orphaned by this diff's own deletions:
  the clean liveness run is the coverage; dead code has no tests to demand.
  The surviving suite must still pass. In the test-alive case, delete the
  symbol and its tests together and verify with the full remaining suite.
- **Text-only edits** — stale narrative, comment rewrites, finishing a
  rename: the post-apply verification suffices.
- **Never apply — report only:** approach findings, unless the user asks for
  that approach; ambiguous findings and anything phrased as a question;
  findings that rest on an assumed reading of the intent; *accidental but
  justified* shapes (isolating and labeling is the author's call); tangled
  ride-alongs (splitting is the author's decision); flag-management/config-
  side removals that need a rollout; compound multi-file restructures
  (compound means moving behavior between files or replacing one shape with
  another across files, such as unifying two data shapes or merging modules;
  deleting a parameter and fixing its call sites, or deleting a dead symbol,
  is not compound); findings a previous report for this branch already
  presented — the author has seen and not taken them; and all pre-existing
  complexity.

Apply and verify one finding at a time — apply, run the baseline's
verification, keep or revert — so a failure indicts exactly one edit; after
any revert, re-check that later findings' premises still hold. A failure
reverts that finding's edit completely and demotes it to a report entry
carrying the new-against-baseline failures as evidence; never leave an edit
half-applied, and never weaken a test to keep one. A mechanical fix may
force a few out-of-diff lines — the config entry orphaned by an in-diff
deletion, a rename's missed call site: edit the minimal set and list each
forced line in the finding's Status; a fix needing more than that is
report-only.

A local finding inside code an approach finding would replace is still
applied when it clears the gate, because the author may decline the
approach. No local finding, wherever it sits, is applied when it deletes or
changes something an approach's sketch or reuse receipt depends on: it is
report-only, gate "the approach depends on it". After each applied edit,
re-check that every approach finding's premises still hold; if one no longer
does, revert that edit and report it under the same gate.

When the user asks for an approach finding to be applied, apply its
prototype diff as one unit, rewritten tests included. It is exempt from the
compound and out-of-diff bars, not from the dirty-file rule. Verify it
against the baseline like any other edit, and list each rewritten test in
Status with the requirement it still checks.

Follow each finding's own edit recipe (its Cleaner shape) and leave
everything uncommitted for the author to keep or revert; commit only if
asked.

## The report

The bar first: a finding the author reads and declines to act on is a defect
of this report, not of the author — when in doubt, the candidate goes to
Dropped candidates. Report at most one approach finding (two only when they
touch unrelated parts of a split change) and at most six local findings,
ranked by consequence. Applied findings are exempt from that cap — every
edit surviving in the tree appears in full with its Status. As the diff
grows, raise the evidence bar and shorten the report, never lengthen it;
weight severity by churn — the same shape matters more in a
frequently-changed file than in a stable one.

The report is for the author, not a log of this procedure. Do every step;
show only what the author needs to act: the findings, the evidence that
would convince them, and the intent you judged against. Never put this
skill's own vocabulary on the page — step numbers, ledger, braid, rung,
receipt, phantom, move, never-flag — and never narrate the procedure ("the
sketch was written before reading the diff", "no phantom claims"). Say what
you checked in plain words ("I ran the branch's tests on the alternative: 10
passed"). Write in a neutral tone: describe the code, not the author, and
use no superlatives.

Open with the tree state in one line — how many findings were applied, which
files changed, and the verification result — so the author knows before
reading anything else whether their working tree moved. Then one or two
sentences that answer the request: the main simplification, or that the
change is already in its simple form. Then the scope (base commit, what was
scanned) and the intent record, in plain words.

Each finding, in this structure:

- **Title** — one specific imperative sentence: what becomes simpler and why
  ("delete the three-way branch — the general path already handles X").
  Question form, always conditional ("if X holds, delete Y?"), is reserved
  for findings demoted to a question: the Ambiguous verdict, name-search
  evidence, an assumed intent, an unmapped coverage line, or an approach
  that could not be prototyped.
- **Where** — file:line.
- **Shape** — the catalog name plus the mechanical fix type; for an approach
  finding, what it does in plain words ("fix it in the loader").
- **Evidence** — the citations and receipts that survived Step 7; before/
  after structural counts where they help (max nesting 4→2, params 5→3),
  never composite scores. Report only counts you can point at with
  file:line; drop a count you cannot cite.
- **Impact** — which cost it removes: change amplification, cognitive load,
  or unknown unknowns (what a reader cannot see must change). Claim
  comprehension cost, never defect or maintenance economics — those don't
  follow from shape alone.
- **Cleaner shape** — an edit recipe in small behavior-preserving steps,
  landing as its own structure-only commit, separate from behavior changes,
  when the author lands it; compound multi-file restructures get staged or
  demoted to follow-up. An approach finding that changes behavior anywhere —
  data migrated, a new error a caller can see — says so and is not called
  structure-only.
- **Behavior preservation** — every requirement the shape touches; the test
  coverage status; if uncovered, the test that would make the edit safe.
- **Severity × disposition** — issue / suggestion / nit, crossed with:
  before merge / fine as a follow-up PR / question for the author. Pin
  severity to the concrete consequence, not the persuasiveness of the
  write-up; every finding is non-blocking, and the author decides whether to
  keep an applied edit or act on a report-only one. Signature- and
  hierarchy-crossing recommendations carry the highest regression risk —
  weight them down.
- **Status** — *applied* (files touched, any forced out-of-diff lines, and
  the verification receipt: the command run and its result against the
  baseline); *applied, then reverted* (the new-against-baseline failure as
  the receipt); or *report-only*, saying in plain words what stopped it —
  approach finding, the approach depends on it, ambiguous verdict, assumed
  intent, author's-call shape, uncovered behavior, dirty file,
  rollout-gated, compound restructure, out-of-diff bound exceeded,
  unverifiable here, or a question-phrased / user-requested report-only run.

An approach finding adds the Step 7 bar's fields after Evidence: Coverage
map, Counts (diff → alternative, in plain words: "helpers 2 → 0, patched
call sites 3 → 0"), Prototype (what item 5 ran, deleted or rewrote, and
compared), Switching cost and Unless. The local findings it would supersede
fold into it under **If you keep the current approach**, one line each: the
edit and its evidence in one sentence, enough to act on. An applied one also
keeps its full entry; root-cause grouping never merges applied edits away.
An approach finding is a suggestion; it is an issue only when the prototype
shows the current diff failing a requirement. It is "before merge" when
switching costs no more than the diff itself and removes new state or public
surface; otherwise it is a follow-up or a question.

Order the report: the approach finding, if any; then local findings in this
change; then pre-existing complexity the diff touches (labeled as such,
never mixed in); then open questions, each one whose answer changes what the
author does — drop a question the report's own analysis already answers;
then **Dropped candidates** — one line each: the shape or move, and the
evidence that killed it. Group findings that share one root cause into a
single entry. Report at most three nits and summarize the rest as a count.
If a previous reduce-complexity report exists for this branch, do not
re-report what it already said. If nothing survives, the report is short:
the base commit, the intent record, what was scanned, the simpler approach
you tried and why it does not win (one or two sentences), and the strongest
candidate with the evidence that killed it.

Keep recommendations proportional to an in-review change. For the residue
scan, the change's primary new surface is presumed intentional design —
recommending its wholesale dissolution requires wrong-abstraction evidence,
not taste. Only an approach finding that clears Step 7's bar may propose
replacing it. When the intent is an urgent fix, prefer the smallest
alternative and list any larger redesign as a follow-up. Skip polish on code
that is feature-flagged, experimental, or slated for deletion; suppress
praise notes, out-of-diff opportunities other than an approach finding's
named fix location, linter territory, and questions that only ask for
explanation.

A worked example of one local finding:

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
> **Status:** applied — `src/export.py`, `src/cli.py`, `src/batch.py`,
> `tests/test_export.py` edited, no forced out-of-diff lines;
> `pytest tests/test_export.py` 23 passed, full suite matches the green
> baseline (412 passed). Left uncommitted for review.

A worked example of an approach finding, abbreviated:

> **Title:** Expand `~` once in `config.load()`, as `cache_dir` already
> is — the three call-site expansions and the `_home_path` helper then go.
> **Where:** `app/config.py:27` (the fix location, outside the diff);
> replaces `app/upload.py:12`, `app/export.py:40,88` and
> `app/paths.py:1-9`.
> **Shape:** fix it where the problem starts.
> **Evidence:** `Config(` is built only at `app/config.py:22`; every
> consumer reads `config.output_dir`; `config.py:29` already applies
> `os.path.expanduser` to `cache_dir`.
> **Coverage map:** R1 `~/out` in the config file writes under the home
> directory → `config.py:27`; R2 an absolute path is unchanged →
> `expanduser` leaves it as is; compat: the `--output-dir` flag still
> overrides the file → `cli.py:31`, untouched.
> **Counts:** places that expand `~` 3 → 1; helpers 1 → 0; files touched
> 4 → 1. The alternative uses `os.path.expanduser`, which `config.py:29`
> already calls and `tests/test_config.py:14` already tests, instead of a
> new helper.
> **Prototype:** I applied the edit to a copy of head; `pytest` 84
> passed; `test_home_path_expands` rewritten to load a config with `~/out`
> instead of calling the deleted helper, and it passes against head too;
> `~/out`, `/abs/out` and `out` give the same paths through head and the
> prototype.
> **Switching cost:** about 20 lines removed, 1 added; one test rewritten;
> no stored data.
> **Unless:** a plugin outside this repo calls `_home_path`; the
> `pyproject.toml` entry points list none.
> **If you keep the current approach:** inline `_home_path` (`paths.py:3-5`), a one-line wrapper
> over `os.path.expanduser`, at its three call sites (unearned
> indirection).
> **Severity × disposition:** suggestion / before merge.
> **Status:** report-only — approach finding.

And a worked example of a candidate that dies in Step 7:

> `retry_wrap` in `src/jobs.py:74` pattern-matched dead scaffolding — no
> call-syntax references anywhere in the final tree — but the liveness
> protocol's quoted-string grep (step 2) hits `config/jobs.yaml:12`, which
> wires it up as a queue callback, an entry point the call-graph reading
> missed. It costs one line in the report:
> **Dropped candidates:** `retry_wrap` (dead scaffolding) — apparent zero
> references, but consumed via `config/jobs.yaml` queue wiring.
