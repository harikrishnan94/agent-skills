---
name: humanize
description: >-
  Hold generated code to the bar a careful human author meets before a reviewer
  sees it. Use whenever writing or modifying code a human will review — a PR, a
  patch, a commit on a shared branch — and when cleaning up an existing diff on
  explicit cues like "humanize this", "this looks AI-generated", "AI slop",
  "reviewers keep flagging generated code", or "clean this up before I open the
  PR". Applied to an existing diff it fixes the code by default and reports what
  changed. Removes narration comments, theatrical error handling, padding, and
  generated-looking collateral; keeps the comments, commit message and PR text
  in plain sentences; adds the edge-case handling generated code tends to miss.
  Improves quality — never hides AI involvement where a project requires
  disclosure.
---

# Humanize: meet the reviewer's bar

Reviewers reject generated code for a predictable set of tells. Every one of
them is a real defect — noise, padding, theater — so removing them is ordinary
quality work, not camouflage. Two things this skill is not:

- **Not detection evasion.** Where a project requires AI disclosure, the
  disclosure stays. The goal is a diff no reviewer has *reason* to flag, not a
  diff that hides its origin.
- **Not manufactured messiness.** Never inject typos, irregular formatting, or
  deliberate imperfections to "look human" — tools that do this produce worse
  code, and reviewers spot the fake as fast as the tell. A careful author's
  work is minimal, not messy.

## Two modes

**Write mode** — the default whenever you are authoring or modifying code.
Every rule below applies as you write. There is no extra workflow; the bar is
simply the bar.

**Fix mode** — the user points you at an existing change ("humanize this
diff"). Scope is the change set they name; when they don't, use the working
tree plus the current branch's diff against its merge base with the integration
branch, and ask if that's ambiguous. Fix the code directly, then report what
changed. Never touch lines outside the change set — unsolicited reformatting of
untouched code is itself a tell.

**The guardrail governing both modes:** never delete a guard, a comment, or a
branch solely because it looks generated. Verify it is actually dead or
redundant — read the caller, the type, the test — before removing it. Guards
deleted on reflex have broken production before. If you cannot verify, leave it
and say so. And when a comment is bad, prefer rewriting it into a true, useful
one over deleting it.

## Read the neighbors first

Before writing or judging anything, read the surrounding code: naming style
(including terse abbreviations), error-handling idiom, comment density, test
structure, file organization. The repo's own style beats every default below.
Where a rule here gives a number, the codebase's actual habit wins.

**Reuse before write.** Before adding a helper, search for existing code that
already does the job — grep for the operation, check what the neighboring
modules import. Reimplementing what the project already has is among the
strongest tells, and a maintenance bug regardless.

## Comments: the loudest tell

Comments explain *why*, never *what*. A comment carries only what is
non-obvious from the surrounding code: intent, an invariant, a hazard, a
consequence the reader cannot see from here, the meaning of a dense regex or
bit trick. Add one only when it materially helps a reviewer or reader grasp the
code. When in doubt, do not add it — and cut the one already there.

- Never narrate the next line. If the comment shares its words with the code it
  says nothing — carry a different fact or delete it. Write for a reader who
  knows the language better than you do.
- One comment per fact. Explaining the same thing at the declaration and again
  at the use site is a tell.
- Match the file's comment density. When the neighbors give no signal, stay
  under roughly ten added comment lines per diff.
- Banned outright: self-referential comments ("as requested", "updated to fix
  the issue"), placeholder comments ("implement as needed"), section banners,
  ownerless TODOs (use `TODO(name)` where the repo does).
- All of this applies to test files with full force — test code is where
  generated comment style lingers longest.

Cut a comment because it restates the code, not because you cannot follow it.
Where you cannot tell whether its fact is real, the guardrail wins: keep it and
say so.

Before:

```python
# Loop through all the users and check each one
for user in users:
    # Skip inactive users
    if not user.active:
        continue
        ...
```

After:

```python
for user in users:
    # suspended accounts keep their slot for 30 days, so skip, don't evict
    if not user.active:
        continue
        ...
```

One comment survived — the one carrying a fact the code cannot say.

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
- Say what the thing is, not the project's private name for it. Keep a term
  only when it is the field's shared name and no ordinary words replace it.
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
// The cached object has to stay clean.
```

For prose outside the change — a Slack message, a mail, a review reply — use
the `plain-prose` skill where it is installed. It carries the full rules, the
per-rule tests, and the research the numbers come from.

## Robustness: guard what's real, drop the theater

Generated code gets defensiveness backwards: elaborate handling for states that
cannot occur, nothing for the edge cases that actually arrive. Fix both
directions.

**Delete** (subject to the guardrail above):

- blanket try/catch that logs and continues, or swallows the error entirely
- retries around operations that are not transient
- checks for conditions the type system or the caller already guarantees
- the same invariant re-validated at every layer

**Add** — the checks generated code actually omits:

- empty collections and boundary indices
- null/absent values at real data boundaries: user input, file and network IO,
  responses from external services
- error propagation the caller genuinely needs

Where you can, restructure so the error case cannot occur at all — a tighter
interface beats a guard.

Before:

```python
def load_cfg(path):
    try:
        return json.loads(read_file(path))
    except Exception:
        logger.error("config load failed")
        return DEFAULT_CFG
```

After:

```python
def load_cfg(path):
    cfg = json.loads(read_file(path))     # missing/invalid config must abort,
    cfg.setdefault("timeouts", {})        # not silently run on defaults
    return cfg
```

The blanket catch hid real failures. The case that does occur — a config
without the optional section — is now handled directly.

In fix mode, an added guard is a behavior change. Apply it, but list it in its
own section of the report, so the reader sees behavior changes apart from style
fixes.

## Every line must earn its place

Re-read the diff and delete anything the change works without:

- dead branches, speculative parameters, config knobs, "for future use" hooks
- wrapper types, forwarding functions, single-use abstractions — no new
  abstraction until roughly three real call sites exist; duplication is cheaper
  than the wrong abstraction
- redundant else after return, logging no one will read

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

- Run the changed path, not just the compiler or the test suite.
- Confirm every API you call exists in the version this project actually pins —
  open the dependency's source or docs; memory is not a source.
- Code you have not run does not meet the bar.

## Commits, PR text, and the disclosure gate

- Commit subject: one short imperative line naming the change, in the
  repository's existing style (read the recent history). Body, when needed:
  prose explaining why — no bullet scaffolding, no "This commit…", no emoji.
- Independent changes go in separate commits, not one mega-diff.
- PR description: what the reviewer needs and why the change exists, in prose,
  under ~2,500 characters. No emoji, no header-and-bullet scaffolding on small
  changes, no politeness filler.
- No unsolicited collateral: no new design-note or summary markdown, no README
  or LICENSE edits nobody asked for. Files end with a newline.

**The disclosure gate:** before writing trailers or PR text, check the
project's contributing docs for an AI-contribution policy.

- Disclosure mandated (e.g. an `Assisted-by:` trailer) → include it. Removing
  mandated attribution is prohibited, full stop.
- AI contributions banned → stop and tell the user instead of polishing the
  change.
- Policy silent → follow the user's and the tool's own defaults.

This skill governs quality; it never conceals provenance.

## Final review: fresh eyes

Re-read the full diff as a reviewer who did not write it and has rejected
generated code before, asking of each hunk: *what here would make me suspect
this diff, and is it justified?* Where the host supports it, prefer a genuinely
fresh pass — a new session or a second reviewer. The session that wrote the
code defends its own choices instead of cutting them.

The closing checklist:

- every surviving comment explains a why the code cannot show
- prose reads as short, one-idea sentences in ordinary words
- guards are real in both directions: theater gone, actual edge cases covered
- every called API verified against the pinned version
- untouched lines untouched
- collateral within bounds; no stray files
- disclosure policy honored

In fix mode, close with the report: what changed and why, grouped by tell;
behavior-affecting additions listed separately; anything intentionally left
(unverifiable guards, mandated trailers) with the reason.
