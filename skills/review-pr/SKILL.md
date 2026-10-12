---
name: review-pr
description: >-
  Review a GitHub pull request written by someone else the way Hari does, and
  return his default review package: what the PR does, answers to the
  questions he would ask, verified findings, and draft comments for his
  approval. Use whenever asked to review, assess, explain, sanity-check or
  comment on another author's PR: "review PR #N", "let's review <url>", "what
  does this PR do", "is this PR valid", "can I approve this", "draft review
  comments", or a re-review after the author pushed. Use it together with, and
  in preference to, a repository's generic review skill. Not for PRs Hari
  authored (use watch-pr, reduce-complexity, humanize).
---

# Review someone else's pull request

Hari reviews to understand a change first, then decides what is worth saying.
The default deliverable is one package in chat: a self-contained visual
explanation, verified findings, and a few draft comments in his voice. Nothing
is posted until he says "post".

## Ground rules

- **Review only.** No edits, commits, pushes, labels or posts before an
  explicit "post". Read the head with `git fetch origin pull/<N>/head`, then
  `git show "${sha}:${path}"` and `git grep <pattern> "${sha}"` (quoted for
  zsh). Never check out or create branches in Hari's tree.
- **Authorship.** If the author is `harikrishnan94`, stop: this skill is for
  other people's PRs.
- **Pin the head SHA** at the start; re-check it before posting.
- **Say what you traced and what you ran.**

## Workflow

```text
- [ ] 1. Gather   - [ ] 2. Explain   - [ ] 3. Structural passes   - [ ] 4. Evidence
- [ ] 5. Verify   - [ ] 6. Choose    - [ ] 7. Draft               - [ ] 8. Present and stop
```

Steps 9 (post) and 10 (re-review) run only when Hari asks.

### 1. Gather

- `gh pr view` (body, author, base and head SHAs, files, commits, reviews,
  comments, checks, linked issues), `gh pr diff`, review threads, linked
  issues, and any PR named as the cause of a regression.
- Existing human and bot reviews: do not repeat them; check bot blockers
  against the mechanism.
- CI failures this PR causes.
- The repository's own review skill, if any: apply its gates, not its output
  format. For ClickHouse, read [references/clickhouse.md](references/clickhouse.md).
- Whether the author is a human or an AI agent account.
- Hari's open PRs that touch the same files
  (`gh pr list --author harikrishnan94 --state open --json number,files`).

### 2. Explain

Hari reads this instead of the PR description and the code, so it must stand
on its own. Write these parts in order. Keep every part; if one does not
apply, say why in one sentence.

1. What the PR changes and what that gains, in one or two sentences.
2. Context: what the touched component does, when it runs, what it hands on.
3. Problem: what goes wrong today and for whom, with the issue's numbers.
4. Before → After: an ASCII or Mermaid diagram with steps in execution order
   and the changed step marked, then one worked example with concrete values.
   For a regression fix, show before the regression, the regression, the fix.
5. What the PR promises, and what it leaves unchanged.
6. How the code does it: one sentence per key change, with the identifier in
   backticks after its description.
7. Performance: a gains table (before, after, time saved, setup). Then the
   costs added against the base branch, when the new path helps and when it
   does not, and the settings or algorithms affected. No numbers from the
   author is a finding.
8. Correctness and safety: invariants, failure paths, concurrent writers and
   their cost, compatibility, defaults.
9. Interaction: callers, sibling implementations, other algorithms, engines
   or modes, and Hari's overlapping PRs.

Within those parts, answer what Hari would otherwise ask. Which inputs
actually take the new path? Build side or probe side? Where does each
threshold come from? How did it work before? Does the PR cover everything its
title claims?

Problems you notice go to Findings. Pass every line of this section, diagram
labels included, through `plain-prose`.

### 3. Structural passes

- `reduce-complexity`, invoked as "report only", on the production diff
  `<base sha>..<head sha>` (not a checked-out branch).
- `humanize` fix-mode checks on the PR's code comments and description, as a
  report: list what it would change and edit nothing.
- `plain-prose` on the PR description and changelog entry.

Fold the results into Findings in your own words. Drop what fails a check
against the source, and pre-existing issues the PR does not touch.

### 4. Evidence

Run the checks in [references/evidence.md](references/evidence.md) that apply.

### 5. Verify

- Re-check each finding at the pinned SHA. For a "dead" or "unused" claim,
  grep every caller and implementation.
- Get one independent challenge unless the PR only touches tests or docs, or
  changes a few lines with no behavior change. Give a fresh-context reviewer
  the PR URL, the SHA and the stated contract, but not your findings. Drop
  what does not hold. A forked reviewer that inherits your context is not
  independent.
- Label each correctness issue as an incomplete fix or a new regression.
- When a trace and a measurement disagree, trust the measurement and report
  the conflict.
- Do not build or benchmark by default. Propose the experiment from
  evidence.md and ask.

### 6. Choose

Verdict, first row that applies:

| Situation | Verdict |
| --- | --- |
| CI broken by the PR, a correctness bug, or no evidence for its main perf claim | Request changes |
| The author's answer decides it | Comment |
| Only non-blocking asks | Approve with the suggestions |
| Nothing to raise, or a correct test-only PR | Approve ("LGTM" / "Test only changes.\nLGTM.") |

Comments:

- One to five, one ask each, related points merged. If one comment makes
  another moot, keep the bigger one.
- Settled questions stay in chat.
- What the PR touches is fixed in this PR, never "fine as a follow-up". Work
  outside the PR's intent goes to a separate PR.
- Raise a pre-existing behavior only when the PR changes its cost, and say it
  predates the PR.

### 7. Draft

Write each comment with `hari-voice`, then pass it through `plain-prose` and
`humanize`. Then apply [references/comments.md](references/comments.md);
its review rules override `hari-voice` where they differ.

### 8. Present and stop

```markdown
## <title> (#<N> by @<author>): <verdict>
<direct answer to Hari's question>

### What it does
<the nine parts from step 2>

### Findings
- **Blocking** / **Non-blocking** <finding>. Evidence: <what you checked>.

### Not raising
- <candidate>: <why>

### Draft review (event: APPROVE | COMMENT | REQUEST_CHANGES)
Body: <text>
1. `<path>:<line>` <comment>

Verification limits: <traced vs run, what you could not access>
```

End by asking which comments to post or change.

### 9. Post

Only after an explicit "post". Follow the posting steps in comments.md. Use
Hari's exact edits. Approved comments post as his, without the 🕵 marker.

### 10. Re-review

Diff the last reviewed SHA against the new head. Mark each earlier comment
addressed, partly addressed, or open. Check new issues and CI. Lead with
whether it is approvable.
