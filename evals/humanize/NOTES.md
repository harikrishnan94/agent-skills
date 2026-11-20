# humanize evals — notes

How to build a fixture, run an agent and grade the result: `../README.md`.

| Eval | Fixture | Grader | What it checks |
|---|---|---|---|
| 1 `authoring-snooze-feature` | `taskrunner` | `check_authoring.py` | a new feature written in the repository's own style |
| 2 `fixmode-burst-limits-cleanup` | `ratelimiter` | `check_fixmode.py` | cleaning up an agent-written change: narration, wrapper class, stray file |
| 3 `collateral-commit-pr-policy-gate` | `contribproj` | `check_collateral.py` | commit message, PR text and a mandated AI disclosure |
| 4 `fixmode-change-story-comment` | `tabsplit` | `check_changestory.py` | a comment that tells the story of the change is deleted; a hazard comment stays |

## What has been measured

Scores depend on the model. Each line names the date; none carries over to a later model.

- **2026-07-13, evals 1 to 3.** With the skill 100%, without it 95% (3 runs per configuration).
- **2026-11-19 and 2026-11-20, eval 2.** 4 of 7 for every skill version tried, with the same three
  failures: `dead_defensive_catch_removed`, `real_edge_guard_added`, `summary_md_deleted`. The
  runs decline to remove the broad `except` and to add the guard, because the prompt says "don't
  change what it does", and they do not commit the deletion of `SUMMARY.md`. Why this fell from
  7 of 7 in July was still being looked at when this was written. Treat 4 of 7 as today's floor,
  not as a regression caused by a skill change.
- **2026-11-20, eval 4**, model `claude-fable-5-2`, 4 runs per skill version.
  - Skill before the commit "humanize: delete change-story comments": the story comment was
    shortened and kept in 4 of 4 runs.
  - Skill at that commit: the story comment was deleted in 4 of 4 runs. The hazard comment was cut
    from two lines to its first sentence in 4 of 4 and never deleted.
  - Owner decision the same day: a hazard comment cut down to the fact that exists nowhere else
    counts as kept. `expected_output` and the grader follow that.

Eval 4 has a companion that is not in this repository: an agent-written ClickHouse pull request
where a maintainer deleted a two-line change-story comment by hand. It needs a ClickHouse
checkout. On it the skill before that commit rewrote the comment (1 run) and the skill at that
commit made the maintainer's exact edit in 4 of 4 runs.

## Eval 4: what its grader can tell

`check_changestory.py` checks place and wording, not meaning. Its docstring lists the rules and
the known gaps. `proof_changestory.py <out-dir>` rebuilds the proof: 37 edits the grader must
grade correctly (15 that must pass, 22 that must fail) and 8 edits it grades wrongly, each pinned
with the grade it really gets.

The grader's rules were changed three times after the runs it grades, each time because an
independent reviewer built edits it graded wrongly. The graded runs have the same pass/fail
pattern under every version.

## Open questions

- A hazard comment that is reworded, not just shortened: the grader passes it when it matches a
  phrase pattern. Whether that should count as kept has not been decided.
- One rule added in that commit has not been tested against a hazard: a comment that defends a
  line is dropped when a test fails without the line and the commit message says why it is
  there. No fixture has a hazard comment in that position.
- The fixture's hazard comment was reworded once before the candidate runs. The earlier wording
  ("Test the rounded amount, not the balance") was never shown to the skill at that commit.
