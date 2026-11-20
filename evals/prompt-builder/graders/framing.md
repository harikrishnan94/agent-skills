# Shared builder + executor framing (frozen — identical across arms, rev 2)

## Builder

The builder agent's prompt is assembled as:

    {SKILL_BLOCK}{BRIEF}

    Write a complete, self-contained task prompt that an autonomous agent will
    execute to accomplish this. The agent that runs your prompt will have no
    other context — everything it needs must be in the prompt itself. Write the
    finished task prompt to {OUTPUT_PATH} and nothing else there. Your final
    message should be one line confirming the file was written.

For the `with_skill` arm, SKILL_BLOCK is:

    <system-reminder>The following skill has been loaded into your context to
    help with this request:

    --- skills/prompt-builder/SKILL.md ---
    {VERBATIM SKILL.MD BODY INCLUDING FRONTMATTER}
    --- end of skill ---
    </system-reminder>

followed by a blank line. For `without_skill`, SKILL_BLOCK is empty.

For rigor-track briefs, one sentence is appended after BRIEF (identical in both
arms):

    The repository in question is at {FIXTURE_PATH}; you may read its files
    while writing the prompt, but do not execute anything in it (no running
    tests, scripts, or builds).

## Executor (rigor track)

The executor agent's prompt is exactly:

    Execute the task prompt in {PROMPT_PATH}. Work in {REPO_PATH}. When you
    are done, write your final summary to FINAL.md in the working directory.

FINAL.md is the arm-identical grading channel for all text checks. The line was
audited for rigor vocabulary: it contains none (no "evidence", "verify",
"sources", "review"). Budget: 45 minutes wall-clock; a run with no FINAL.md and
no clear final answer is scored `incomplete`, rerun once (DESIGN.md §3).

## Rules

- Nothing else in either framing may mention rigor, evidence, verification,
  oracles, review, or testing — that pressure must come from the skill (via the
  generated prompt) or from the builder's own judgment.
- Every generated-prompt.md is leak-audited against the fixture's
  `grader/leak_terms.txt` before its executor run (DESIGN.md §3): LEAKED →
  regenerate once (logged); leaked again → keep, report metrics overall and
  excluding-leaked.
