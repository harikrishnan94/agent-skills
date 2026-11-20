# Skill evals

Regression tests for the skills in `skills/`. Each eval gives an agent a small repository with a
known problem, lets it work with or without the skill, and checks the result with a script.

These are not a benchmark. The graders check structure and wording, and the scores depend on the
model that runs the eval.

## Layout

```
evals/<skill>/
  evals.json                       the evals: prompt, fixture, grader, assertions
  files/<fixture>/setup_fixture.sh builds the fixture repository
  files/<fixture>/...              the files the script assembles into commits
  graders/                         one checker per eval, plus shared helpers
evals/<skill>-workspace/           run output; ignored by git
```

| Suite | Evals | What it tests |
|---|---|---|
| `humanize` | 4 | writing and cleaning up code a human will review |
| `reduce-complexity` | 7 | finding and removing complexity a change does not need |
| `prompt-builder` | 18 briefs, 5 fixtures | whether the prompts the skill writes are well built, and whether they make the executing agent rigorous |

Each suite keeps its own notes: `humanize/NOTES.md`, `reduce-complexity/NOTES.md`, and
`prompt-builder/DESIGN.md` with `prompt-builder/NOTES.md`. They say how that suite is run and
graded and what it has measured. The steps below are the common part.

## Run one eval by hand

1. **Build the fixture** into an empty folder outside this repository:

   ```bash
   bash evals/humanize/files/ratelimiter/setup_fixture.sh /path/to/run/repo
   ```

   The script creates a git repository with a base history on `main` and the change under test
   on a branch. A fixture repository cannot be committed here, because it has its own `.git`.
   `humanize/files/tabsplit` also writes the pull request text to `/path/to/run/pr-context/PR.md`.

2. **Run the agent.** Start a fresh agent with the skill under test, point it at the fixture
   repository, and give it the eval's `prompt` from `evals.json`. For a baseline, run the same
   prompt without the skill.

   The agent must not be able to read this folder. The fixtures hold planted defects and the
   graders say what to look for.

3. **Grade the result:**

   ```bash
   python3 evals/humanize/graders/check_fixmode.py /path/to/run/repo
   ```

   The grader prints a JSON array with one object per assertion: `text`, `passed` and
   `evidence`. It exits 0 when every assertion passes and 1 otherwise. The assertions are listed
   in `evals.json`.

## Requirements

`python3` (standard library only; the fixtures use `unittest`), `git` and `bash`. No network.

## When you change an eval

- Show that the grader can fail. The untouched fixture must fail the assertions for the planted
  problems, and a correct edit made by hand must pass all of them.
  `humanize/graders/proof_changestory.py` is an example: it builds one fixture copy per edit and
  compares each grade with the grade written down for it.
- Write down what the grader cannot tell. A grader that matches words passes an edit that keeps
  the words and loses the meaning. Pin such cases with the wrong grade they get, so a later
  change to the grader shows up.
- Read the evidence when a run passes on a rewording.
- A changed fixture or grader needs fresh runs of both the old and the new skill. Scores from
  before the change do not carry over.
- Keep run output in `evals/<skill>-workspace/`. It is large and it is ignored by git.
