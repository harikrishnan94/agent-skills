---
name: humanize
description: >-
  Reduce unnecessary code and comment lines so reviewers can understand and
  verify a change without the author's agent history. Use whenever writing or
  modifying code a human will review — a PR, a
  patch, a commit on a shared branch — and when cleaning up an existing diff on
  explicit cues like "humanize this", "this looks AI-generated", "AI slop",
  "reviewers keep flagging generated code", or "clean this up before I open the
  PR". Applied to an existing diff it fixes the code by default and reports what
  changed. Removes verbose comments, planning leftovers, unexplained labels,
  and redundant code while preserving behavior and useful rationale. Keeps
  comments, commit messages and PR text in plain sentences. Honors required
  AI disclosure.
---

# Humanize: meet the reviewer's bar

Make the change understandable and verifiable by a reviewer who knows the
language and relevant domain but has none of the author's prompt, plan, or
conversation history. Reduce unnecessary code and comment lines. Preserve
behavior, established terminology, and the facts needed to assess correctness.

The reviewer should find necessary context in the diff, repository, and change
description. Put explanations needed for later maintenance near the relevant
code or in its existing documentation. Remove the authoring story; retain
verified constraints and decision reasons that still matter.

Never hide required AI disclosure or introduce deliberate imperfections to
make code look human. Clear code may need no changes.

## Two modes

**Write mode** — the default whenever you are authoring or modifying code.
Every rule below applies as you write. There is no extra workflow; the bar is
simply the bar.

**Fix mode** — the user points you at an existing change ("humanize this
diff"). Scope is the change set they name; when they don't, use the working
tree plus the current branch's diff against its merge base with the integration
branch, and ask if that's ambiguous. Fix the code directly, then report what
changed. Preserve existing behavior, including failure behavior, unless the
task authorizes a behavior change. Report newly found bugs separately when
they are outside that scope. Keep cleanup within the named change; avoid
unrelated reformatting or refactoring.

**The guardrail governing both modes:** never delete a guard, a comment, or a
branch solely because it looks generated. Verify it is actually dead or
redundant — read the caller, the type, the test — before removing it. If you
cannot verify, leave it and say so. Delete a redundant comment without adding
a replacement. When it carries a useful fact, preserve that fact in fewer
words where possible. Never invent a rationale to justify keeping code.

## Read the neighbors first

Before writing or judging anything, read the surrounding code: naming style
(including terse abbreviations), error-handling idiom, comment density, test
structure, file organization. Follow explicit project conventions, then the
surrounding code. Where a rule here gives a number, treat it as a fallback;
correctness and necessary explanations take priority.

**Reuse before write.** Before adding a helper, search for existing code that
already does the job — search for the operation and check what the neighboring
modules import.

## Fewer comment lines, with useful facts intact

Aim for fewer comment lines when cleaning a verbose diff and sparse comments
when writing code. Zero new comments is a valid result. Each comment must add
information the intended reader needs and cannot readily get from nearby code.
Useful facts include intent, an invariant, a hazard, units, ownership, and a
non-obvious consequence. Dense algorithms or regexes may need an explanation
of what they do. API documentation must still describe its contract.

- Remove narration of obvious operations, repeated explanations, and summaries
  already expressed by a good name. Improve an unclear name or expression
  before adding prose to explain it.
- State a fact once, where readers need it. Compress wordy explanations while
  preserving their conditions, exceptions, and technical meaning.
- Match the file's comment density. When the neighbors give no signal, aim for
  fewer than ten added comment lines per diff. This is a ceiling to question,
  not an allowance to fill; necessary facts may justify exceeding it.
- Banned outright: self-referential comments ("as requested", "updated to fix
  the issue"), placeholder comments ("implement as needed"), section banners,
  ownerless TODOs (use `TODO(name)` where the repo does).
- Apply the same restraint to tests, docstrings, and block comments. Do not
  move narration into docstrings, a README, or PR text to reduce the count.

Do not delete useful context to meet a count, or pack it into unreadably long
lines. A comment increase needs a concrete explanation of what readers were
missing. When an existing fact is unclear, investigate before cutting it.
Verify factual claims in new or rewritten explanations against the code,
tests, requirements, or documented constraints.

Before:

```python
# Loop through all the users and check each one
for user in users:
    # Suspended accounts retain their slot for 30 days.
    # We must skip them here rather than evicting them.
    # Skip inactive users
    if not user.active:
        continue
        ...
```

After:

```python
for user in users:
    # Suspended accounts keep their slot for 30 days; skip without evicting.
    if not user.active:
        continue
        ...
```

Four comment lines became one; the existing retention rule survived.

## Plain sentences

Every piece of prose the change carries — comments, docstrings, the commit
message, the PR text, and the fix-mode report — gets read by people who did not
write it, and often by people who do not read English as a first language. A
sentence a reader has to parse twice is the same defect as a narration comment:
the writer saved effort and charged the reader for it.

- One idea per sentence: 20 words where you are telling the reader to do
  something, 25 where you are describing.
- Keep each word next to the word it depends on. Difficulty comes from that
  distance, not from length — never split a subject from its verb with a
  clause. A long, straight sentence is fine.
- Start with what the reader knows and end on the new point, as a main clause.
  A point trailing in `..., which is what ...` sits in the sentence's weakest
  spot; cut it loose and make it the next sentence.
- No noun stack longer than three words. Name the actor and use the active
  voice.
- Use the repository's established terminology and ordinary words. Check
  unfamiliar terms as described under naming below.
- Plain is not shorter and never vaguer. Simplify the sentence, never the
  content — a good rewrite is often longer.

Before:

```text
// The value returned by the lookup is used by two consumers that both mutate
// it, which is the reason we hand back a copy here rather than the cached
// object itself.
```

After:

```text
// Both callers mutate what they get, so hand back a copy.
```

For prose outside the change — a Slack message, a mail, a review reply — use
the `plain-prose` skill where it is installed. It carries the full rules, the
per-rule tests, and the research the numbers come from.

## Preserve behavior while removing redundant code

Inspect broad exception handlers, retries, repeated validation, and fallback
paths. Remove them only when their redundancy is established. A broad catch
may implement a required fallback; changing a default return into an exception
changes behavior even if the existing tests pass.

In write mode, handle real boundaries: empty collections, boundary indices,
absent external input, and error propagation the caller needs. In fix mode,
follow the task's behavior constraint. Do not add missing guards as a style
cleanup. Where authorized, prefer a simpler interface that rules out the bad
state; report any behavior change explicitly.

## Every line must earn its place

Re-read the diff against the final requirement. Look for remnants of abandoned
approaches: unused helpers, experimental flags, duplicate paths, temporary
adapters, obsolete test scaffolding, and comments that defend an earlier design.
Check current callers, contracts, and tests before deciding they are obsolete.
Remove only what has no current purpose in behavior, clarity, or validation:

- dead branches, speculative parameters, config knobs, "for future use" hooks
- wrapper types and forwarding functions that add no useful boundary or meaning;
  a single-use helper can still clarify an operation or isolate a real invariant
- redundant else after return and diagnostics left over from development

Prefer touching existing code over adding files; a short function over a class;
an existing mechanism over a parallel one. Size each function to its job —
splitting everything into uniform small functions is itself a tell. Tests get
the same treatment: no assertion padding, no reference outputs beyond what the
assertion needs.

Never, in any mode:

- cast to `any` (or the language's equivalent) to silence a type error
- weaken or rewrite a test so broken code passes
- mask a race with sleep/setTimeout
- mock a service or API that does not exist
- delete a failing method instead of repairing it

Deep structural review of an in-progress change — wrong abstraction boundaries,
accreted layering — is the `reduce-complexity` skill's job where it is
installed; this section stays at the line and function level.

## Shape and naming

- Search unfamiliar names and terms in the code and documentation. Keep
  established domain terms, repository concepts, and conventional abbreviations
  when they are precise. A term is not wrong merely because you did not know it.
- Replace labels whose meaning exists only in the prompt, plan, or conversation
  with names describing their current role. For example, replace a planning
  label such as "phase-two envelope" with the actual object or operation.
  Documented protocol phases or compatibility versions may be real concepts;
  check before renaming them.
- When a necessary new concept has no established name, choose a descriptive
  one and explain its contract once near its definition. Avoid a glossary or
  extra prose for a label that can simply be replaced.
- Names state what the thing is in the domain's terms — neither
  `total_user_input_character_count` nor `data2`. No meaning-free `Manager`,
  `Handler`, `Helper`, `Util`, `Service`, `Info`, `Processor` (unless the
  codebase already uses them).
- Mirror the neighbors' idiom: their abbreviations, their ordering, their file
  layout — not generic best practice.

## Verify before it ships

Exercising the change is part of the bar. Generated code now looks idiomatic
even when it is wrong, so reviewers escalate from style to logic — and logic is
where it fails.

- Exercise the affected behavior with checks appropriate to the change. When
  removing guards or fallbacks, check those error paths too; a passing suite
  alone does not prove that behavior stayed the same.
- Confirm every API you call exists in the version this project actually pins —
  open the dependency's source or docs; memory is not a source.
- Report what ran and any limits. Do not create tests that merely enforce the
  rewritten wording or mirror the implementation.

## Commits, PR text, and the disclosure gate

- Commit subject: one short imperative line naming the change, in the
  repository's existing style (read the recent history). Body, when needed:
  prose explaining why — no bullet scaffolding, no "This commit…", no emoji.
- Independent changes go in separate commits, not one mega-diff.
- PR description: what the reviewer needs and why the change exists, in prose,
  under ~2,500 characters. No emoji, no header-and-bullet scaffolding on small
  changes, no politeness filler.
- No unsolicited design notes or summary files. Update existing documentation
  only when needed for the authorized change. Files end with a newline.

**The disclosure gate:** before writing trailers or PR text, check the
project's contributing docs for an AI-contribution policy.

- Disclosure mandated (e.g. an `Assisted-by:` trailer) → include it. Removing
  mandated attribution is prohibited, full stop.
- AI contributions banned → stop and tell the user instead of polishing the
  change.
- Policy silent → follow the user's and the tool's own defaults.

This skill governs quality; it never conceals provenance.

## Final review: fresh eyes

Re-read the full diff with only the context available to a reviewer. Can you
explain the behavior change, the reason for each non-obvious choice, and how to
check correctness from the diff, repository, and change description?

For substantial changes, use a fresh reviewer or subagent when available.
Give it those artifacts without the authoring conversation or your expected
explanation. Ask it to identify missing context and unexplained terminology.
Repair concrete gaps; do not add commentary merely to anticipate every possible
question. If you review it yourself, do not claim an independent check.

The closing checklist:

- unnecessary comment lines removed; useful facts kept without repeated prose
- every added construct serves the final implementation, not an abandoned plan
- names and explanations make sense without the author's private context
- prose reads as short, one-idea sentences in ordinary words
- behavior preserved, or authorized changes identified and verified
- every called API verified against the pinned version
- untouched lines untouched
- collateral within bounds; no stray files
- disclosure policy honored

In fix mode, briefly report what changed and why, the checks run, and anything
left unresolved. When comments changed, report comment lines before and after
in the cleanup scope, including docstring and block-comment prose. Count text
lines rather than delimiters alone; preserve required notices. Explain an
increase by the missing information it supplies. List authorized behavior
changes separately. Do not produce a separate report file unless requested.
