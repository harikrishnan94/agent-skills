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
- **Pin the head SHA** at the start; re-check it before presenting and again
  before posting.
- **Say what you traced and what you ran.**
- **No step is skipped** for time or tool budget. Each step 1-7 ends up in the
  Review record (step 8) as `done`, `n/a: <reason>` or `not done: <reason>`.
  `n/a` is allowed only where the step names the condition: no review skill in
  the repository, not a ClickHouse repository, the challenge exemption in step
  5, an evidence section that does not apply. Anything else is `not done`, and
  the package then opens with `Incomplete: <steps>.`

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

Record: Author (human or AI agent account), Issues, CI caused by PR, Existing
reviews (bot blockers included), Repo review skill (its gates, or "none in
repo"), Overlapping PRs.

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

Record: Parts n/a, each with its reason, or "none".

### 3. Structural passes

- `reduce-complexity`, invoked as "report only", on the production diff
  `<base sha>..<head sha>` (not a checked-out branch).
- `humanize` fix-mode checks on the PR's code comments and description, as a
  report: list what it would change and edit nothing.
- `plain-prose` on the PR description and changelog entry.

What holds becomes a Finding, in your own words. Drop what fails a check
against the source, and pre-existing issues the PR does not touch.

Record: for each pass, what it reported, what became a finding, and what you
dropped and why.

### 4. Evidence

Run the checks in [references/evidence.md](references/evidence.md) that apply.

Record: one entry for each section of evidence.md (Performance, Correctness,
Tests, Description, Design and scope): `applied` with the checks you ran and
what they showed, or `n/a: <reason>`.

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

Record: Re-checked at (the SHA), Challenger (what it confirmed, what it added,
what you dropped; or the exemption above, named), Conflicts (trace against
measurement, or "none"), Labels (incomplete fix or new regression, per
correctness issue, or "none").

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

Record: Row (the verdict-table row that applied).

### 7. Draft

Write each comment with `hari-voice`, then pass it through `plain-prose` and
`humanize`. Then apply [references/comments.md](references/comments.md);
its review rules override `hari-voice` where they differ.

Record: Passes (those applied to every comment), Greeting (the comments.md
rule used: human, AI agent account, test-only bot).

### 8. Present and stop

Use this format exactly. The headings, part labels, record labels and status
words are fixed; the checker rejects anything else.

```markdown
## <title> (#<N> by @<author>): <verdict>
<direct answer>
Head: <sha> (re-checked before presenting: unchanged | moved to <sha>)

### What it does
**1. Change and gain.** <text>
**2. Context.** <text>
**3. Problem.** <text>
**4. Before → After.** <text>
**5. Promises and unchanged.** <text>
**6. How the code does it.** <text>
**7. Performance.** <text>
**8. Correctness and safety.** <text>
**9. Interaction.** <text>

### Findings
- **Blocking** | **Non-blocking** <finding>. Evidence: <what you checked>.

### Not raising
- <candidate>: <why>

### Draft review (event: APPROVE | COMMENT | REQUEST_CHANGES)
Body: <text>
1. `<path>:<line>` <comment>

### Review record
- **1. Gather:** done
  - Author: <result>
  - Issues: <result>
  - CI caused by PR: <result>
  - Existing reviews: <result>
  - Repo review skill: <result>
  - Overlapping PRs: <result>
- **2. Explain:** done
  - Parts n/a: <result>
- **3. Structural passes:** done
  - reduce-complexity: <result>
  - humanize: <result>
  - plain-prose: <result>
- **4. Evidence:** done
  - Performance: applied: <result>
  - Correctness: applied: <result>
  - Tests: applied: <result>
  - Description: applied: <result>
  - Design and scope: applied: <result>
- **5. Verify:** done
  - Re-checked at: <sha>
  - Challenger: <result>
  - Conflicts: <result>
  - Labels: <result>
- **6. Choose:** done
  - Row: <result>
- **7. Draft:** done
  - Passes: <result>
  - Greeting: <result>

Verification limits: <limits>
```

- `<verdict>` is one of the four in step 6. The review event follows it:
  Request changes is `REQUEST_CHANGES`, Comment is `COMMENT`, and both
  Approve verdicts are `APPROVE`.
- `<direct answer>` answers Hari's question. If any status below is `not
  done`, it starts with `Incomplete: <steps>.`
- Findings and Not raising each hold bullets, or the single word `None.`
- A step's status is `done`, `n/a: <reason>` or `not done: <reason>`. An
  Evidence entry starts with `applied`, `n/a: <reason>` or `not done: <reason>`.
  Give the results as step 1-7 say in their Record lines.
- If the head moved, re-check every finding and anchor, set `Head` to the SHA
  you pinned, and say so in the direct answer.

Then:

1. Write the package to `/tmp/review-pr-<N>/package.md`.
2. Run `python3 "<skill dir>/scripts/check_review.py"
   /tmp/review-pr-<N>/package.md`. Installed copies are symlinks, so resolve
   the skill directory with `realpath` first.
3. Fix the package until the check prints `OK`. A failing check means the
   review is not finished. Then show the same text in chat, and end by asking
   which comments to post or change.

### 9. Post

Only after an explicit "post". Follow the posting steps in comments.md. Use
Hari's exact edits. Approved comments post as his, without the 🕵 marker.

### 10. Re-review

Diff the last reviewed SHA against the new head. Mark each earlier comment
addressed, partly addressed, or open. Check new issues and CI. Lead with
whether it is approvable.
