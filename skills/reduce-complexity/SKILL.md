---
name: reduce-complexity
description: Use when the user wants to find and remove accidental complexity that has accreted in an in-progress change — a PR under review or any feature branch — without disturbing inherent complexity or reviewer-requested shapes. Establishes the change set against a base commit (from the PR, or asked-for/derived for non-PR branches), reads review comments when a PR exists, reviews the change as a whole, and reports concrete, prioritized simplification opportunities. Never applies edits.
---

# Accidental complexity reducer

You are reviewing an in-progress change to find places where it could be expressed
more simply if it had been designed from the start knowing where it ended up.

The change is built up incrementally — fixes that get it working but aren't always
folded back into the design. So it accumulates *accidental* complexity: redundant
branches, special cases bolted onto existing logic, helpers that exist only to paper
over an earlier decision, duplicated logic, or layering that no longer reflects how the
change actually fits together.

Your job is to eliminate accidental complexity while the change is still open, without
disturbing the inherent complexity — the irreducible difficulty that comes from the
problem itself, or from what reviewers explicitly asked for.

## Step 1 — Establish the change set (base commit)

Before reviewing anything, fix the scope: the set of changes to be judged, defined as
the diff between the current branch and a **base commit**. Determine the base commit in
this order, and re-verify with git rather than trusting assumptions:

1. **PR branch (preferred).** Determine the current branch (`git rev-parse --abbrev-ref
   HEAD`) and check whether a pull request is associated with it (e.g. `gh pr view`, or
   the host's PR tooling). If a PR exists, the base commit is the merge-base of the
   current branch and the PR's base branch (`git merge-base HEAD <base-branch>`). Then
   proceed to **Step 2** to read the review.

2. **Non-PR branch.** If there is no PR (or no PR tooling is available), there is no
   review thread — derive or confirm the base commit explicitly:
   - **Ask the user** for the base commit/ref when the intended comparison point is
     ambiguous or important enough to get wrong.
   - **Derive a candidate** from the branch and git history when you can do so
     confidently, then **confirm it with the user before reviewing** (the entire scope
     depends on it). Reasonable derivations, in order of preference:
     - If the branch tracks an upstream, use `git merge-base HEAD @{upstream}`.
     - Else, detect the integration branch that exists (`main`, `master`, `develop`,
       `trunk`) and use `git merge-base HEAD <that-branch>`.
     - Else, inspect history (`git log --first-parent`, divergence point, reflog) to
       find where this line of work diverged, and propose that commit.
   - State the derived base commit, how you arrived at it, and what the resulting diff
     covers, and let the user accept or correct it. Do not silently pick one.

Once the base commit is fixed, the **changed lines** (the diff against it) are the
primary scope. Read surrounding code, call sites, and tests as needed — a shape that
looks redundant in the diff may be load-bearing once you see how it's used.

## Step 2 — Read the review (PR branches only)

When a PR exists, read its review comments — both human and automated (including bots
such as clickhouse-gh). The substance of accepted feedback is a **hard constraint**: a
shape that exists specifically to satisfy a review comment is not accidental complexity
to be removed, even if it looks awkward in isolation.

But the review thread only explains part of the change. Other parts were introduced
later without ever being raised in review, and those are just as likely to be
load-bearing. The absence of a linked comment is **not** evidence that a change is
unjustified or safe to remove. Judge accidental vs. inherent from the code and behavior
themselves, treating the comments as one input rather than a complete map.

For non-PR branches there is no review thread, so this judgment rests entirely on the
code and behavior.

## The distinction that governs everything

- **Accidental complexity** is an artifact of how the change was built up — it can be
  removed by re-expressing the same behavior, with nothing lost. This is the target.
  It tends to show up as: the same condition guarded in several places, a helper that
  only forwards or compensates for an earlier abstraction, behavior steered by a pile
  of booleans where a clearer model would do, new cases appended after the main flow
  instead of integrated into it, or old and new paths coexisting when one could
  subsume the other.
- **Inherent complexity** reflects the genuine difficulty of the problem: edge cases,
  correctness under concurrency, alignment and tail handling, overflow, NULL semantics,
  performance constraints, compatibility, and anything a reviewer specifically
  requested. This must be preserved.
- Before flagging anything, check whether the apparent complexity is doing real work.
  If you can't establish from the available context that it's removable, say so and
  treat it as inherent rather than recommending its removal.

## Judgment

- Preserve the change's intended behavior and the substance of accepted review
  feedback. This is about how the change is expressed, not what it does.
- Review the change as a whole, not commit by commit.
- Don't propose broad redesigns. Keep cleanups proportional to an in-review change,
  unless the complexity is clearly caused by a wrong abstraction boundary.
- Don't flag a cleanup unless you can point to concrete evidence that the current shape
  is structurally more complex than the problem requires.
- It's acceptable — and expected when the change is already clean — to conclude that
  nothing is worth doing.

## Output discipline

- **Do not apply edits.** Describe each opportunity concretely enough that the user can
  implement or reject it. The repository tree is read-only for this skill; use git and
  file reads only.
- For each opportunity, report:
  - **Where it is** — file(s) and the specific shape.
  - **Evidence** that it's accreted rather than essential.
  - **The cleaner integrated shape** it could take.
  - **Why that shape preserves** intended and reviewer-requested behavior — flag it as
    speculative if the surrounding context can't confirm that.
  - **A rough read** on how much complexity it removes against the risk of touching it.
- Lead with the high-value, low-risk opportunities.
