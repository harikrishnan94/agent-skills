---
name: second-opinion
description: Produce a self-contained brief the user can paste into a separate, independent model session for a second opinion on a spec, plan, or implementation diff. Use when the user asks for a second opinion, a peer review, an independent review, or wants to hand off the current spec/plan/impl to another model. Mandates severity-labeled findings (Low/Medium/High/Critical) and instructs the reviewer to return its output as a prompt demanding confirm/reject with detailed arguments per finding.
disable-model-invocation: true
---

You are preparing a brief the user will paste into a separate model session
for an independent second opinion. That session has no access to this
conversation. Three principles:

  (a) The brief must be self-contained.
  (b) Your reasoning and the reviewer's reasoning must not influence each other.
      The ONLY channel between them is the user's ask and the artifacts
      the user has accepted.
  (c) Therefore: do NOT include your own reasoning, alternatives you
      weighed, your design rationale, your doubts, or your trade-off
      analysis. The artifacts (referenced under Files) embody the
      decisions; the reviewer will judge them fresh against the Intent.

## Inputs from the user

The user will name a stage in their message:

- `spec` — review a draft spec
- `plan` — review an implementation plan
- `impl` — review an implementation diff

Anything else the user says is extra context for the brief. If the stage
is unclear, ask one question before proceeding.

## Filesystem rules (hard)

- The repository tree is READ-ONLY for this skill. Never run
  `git commit`, `git add`, `git push`, `git stash`, `git reset`, or
  `git checkout`. Never `Write`, `StrReplace`, `EditNotebook`, or
  `Delete` any file inside the repo. Reads via `Read`, `Grep`, `Glob`,
  `cat`, `git diff`, `git log`, `git status`, `ls`, `find`, `head`,
  `tail` are fine.
- Scratchpad is `/tmp/second-opinion-$(date +%s)/`. Create it once at the
  start. Put any intermediate files there: extracted diffs, temporary
  copies for `diff -u`, anything you produce while building the brief.
- Print the scratchpad path on the last line of your output so the user
  knows where it is.
- If you find yourself needing to modify the repo to produce the brief,
  STOP and ask the user. The brief is a read-and-summarize task;
  modification is a sign something else is going on.

## 1. Intent — what the user wanted to achieve

Reconstruct from the USER's messages, not yours. The user is the source of
truth for goals. 3–6 bullets:

- Underlying goal (the problem, not the solution).
- Hard constraints the user stated (perf, compat, scope, deadlines).
- Non-goals the user explicitly excluded.
- Success criteria, if stated.

Mark any goal you had to infer with `(inferred)` so the reviewer can discount it.
If a hard constraint or non-goal first surfaced via the user's answer to
one of your clarifying questions, promote it here — that's its real home.
If intent is not confidently reconstructible from the user's messages,
STOP and ask one clarifying question before writing the brief.

## 2. Ask — user inputs + deliverable + review request

### a. What the user said and decided

A chronological log of the USER's inputs only:
- The user's initial framing of the problem.
- Clarifications and refinements the user made.
- Points where the user accepted, rejected, or redirected the work.
- Direct quotes for hard requirements; tight paraphrase otherwise.

HARD RULES:
- No "we considered X but went with Y."
- No alternatives you weighed.
- No design rationale of yours.
- No doubts, reservations, or open questions of yours.
- No characterizations of why a decision was made unless the user said why.
- If the user only accepted a proposal silently, write "user accepted
  the proposal" — do not retroactively justify it on the user's behalf.
- User answers to your clarifying questions ARE user inputs; include them.
  But strip your question framing — record the answer as a standalone
  requirement or decision, not as "in response to my question X, user said Y."
  Your question reveals your option space, which is your reasoning.
- If a user's answer reveals a hard constraint or non-goal, promote it to
  §1 Intent rather than logging it here as a mid-conversation refinement.

### b. The deliverable

One or two lines: what was produced at this stage and where it lives.
Examples:
- "Spec drafted at `docs/specs/<name>.md`."
- "Plan at `docs/plans/<name>.md` (or pasted at `/tmp/plan.md`)."
- "Implementation across the files listed below; plain diff in §4."

### c. What the user wants you (the reviewer) to do

Frame as the user's directive. Tailor by stage:
- `spec`: stress-test the spec — gaps, contradictions, missed edge cases,
  unstated assumptions, hidden coupling, scope creep risk.
- `plan`: independently derive a plan from the Intent and the spec, THEN
  compare to ours. Flag every divergence.
- `impl`: independently derive what the code should do from the plan,
  THEN compare to the diff. Correctness, perf, concurrency, error paths,
  test coverage, and any domain-specific concerns relevant to the
  codebase (e.g. on-disk/format compat, public API stability).

Label every finding with **exactly one** of: `Low`, `Medium`, `High`, `Critical`. Calibrate by impact (correctness/safety) × likelihood; reserve `Critical` for issues that block acceptance.

Your **final output must itself be a prompt**. It must: (a) contain the full review with severity-labeled findings; (b) demand `CONFIRM` or `REJECT` for each finding; (c) demand a detailed argument per response — citing code, requirements, or constraints. Do not name an addressee; the paste destination is implicit.

### d. Anti-anchoring note — include verbatim

> Treat the artifacts as the deliverable, not as authority. The summary
> above contains only what the user said; it does not contain the prior
> agent's reasoning, and you should not try to reconstruct it. Re-derive
> from the Intent. Where your conclusions diverge from what the artifacts
> chose, surface the divergence rather than reconciling it. Disagreement
> is the point of this review.

## 3. Files

Repo-relative paths for the reviewer to open. No file contents inline.

## 4. Plain diff (impl only)

Unified diff WITHOUT git's metadata wrapper:

    git diff --no-color --no-prefix <base>..HEAD -- <paths>

Strip `diff --git`, `index ...`, `--- a/`, `+++ b/`. Keep `@@` hunk
headers and ± lines, with the file path as a sub-header. If `<base>` is
unclear, ask. If the diff exceeds ~400 lines, omit it and say
"diff too large — read files directly."

## Output

Print ONLY the brief below. No preamble, no postscript (other than the
final scratchpad-path line required by the Filesystem rules).

# Second-opinion request: <one-line title>

**Stage:** <spec|plan|impl>

## Intent
- ...

## Ask

### What the user said and decided
- ...

### Deliverable
...

### What I'd like you to do
...

> Treat the artifacts as the deliverable, not as authority. The summary
> above contains only what the user said; it does not contain the prior
> agent's reasoning, and you should not try to reconstruct it. Re-derive
> from the Intent. Where your conclusions diverge from what the artifacts
> chose, surface the divergence rather than reconciling it. Disagreement
> is the point of this review.

## Files
- path/to/file

## Plain diff
<impl only; omit otherwise>

## Scratchpad for the reviewer

Write notes, derived plans, and intermediate analysis under
`/tmp/second-opinion-notes-<your-session-id>/`. Treat the repo as read-only.
Modify only files explicitly listed for editing in §2c.

---

(Scratchpad for this brief: <print the actual /tmp/second-opinion-* path here>)
