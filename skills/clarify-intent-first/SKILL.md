---
name: clarify-intent-first
description: Do read-only reconnaissance, then ask targeted clarifying questions before starting work on an ambiguous or underspecified request. Use this at the START of any coding, debugging, refactoring, or investigation task where the request could reasonably be read more than one way — asks like "make this faster", "fix the flaky test", "refactor X", "add support for Y", "look into this regression", "clean this up" — and at the moment a human is about to launch a long or expensive autonomous run. Trigger it even when the request feels clear enough to start on, as long as two plausible readings would produce materially different work. Do NOT trigger it for well-specified requests, one-step lookups, or anything answerable by reading the code. Do NOT let it block an already-running unattended job — see Unattended mode.
---

# Clarify Intent First

The expensive failure in agentic work is not a wrong line of code — it's forty minutes of correct work on the wrong problem. A request like "make the probe path faster" has several honest readings, and the difference between them is a different deliverable, not a detail. Thirty seconds of asking is cheap against that.

There are two ways to get this wrong, and both matter as much as the thing it's trying to fix. Interrogating a senior engineer over a clear request teaches them to stop reading your questions. And blocking a job that nobody is watching, to ask a question nobody will read, wastes the entire run — the precise failure this skill exists to prevent.

So the skill is three things in order: **recon, then gate, then ask.**

## Order of operations

Do not compose a question until you've done the reading. Recon comes first because it usually changes the questions — most apparent ambiguity is a fact you haven't looked up yet, and what survives contact with the code is the part that genuinely lives in the requester's head.

1. **Recon (read-only).** Establish the facts you'd otherwise be asking about.
2. **Gate.** Apply the ambiguity test to what's *left* after recon.
3. **Ask** — one batch, with defaults — or start, if nothing material survived.

Skipping straight to step 3 produces the lazy five-question form that makes people ignore the skill. Arriving with context and one sharp question is worth more than the other four combined.

### Recon is strictly read-only

Read files, search, inspect history, read tests, check the build config, look at callers. Do not edit, write, create, delete, commit, push, install, or change any state. Recon must not become a way to start the work before intent is settled — if it does, the gate is decorative.

### Recon is bounded

Recon is for facts, and facts are cheap; it is not a licence to audit the repository. A handful of targeted reads and searches is the shape of it. If you've spent a dozen operations and the ambiguity hasn't shrunk, that's the signal the ambiguity is about *intent*, not facts — stop reading and ask. Endless recon is just a slower way to stall.

## The gate

After recon, write down the two most plausible remaining readings. Then:

- **Would they produce materially different artifacts — different files touched, different deliverable, different definition of success?** → Ask.
- **Do they converge on roughly the same work?** → Start.

Weight the gate by cost and reversibility. A small reversible edit can absorb a wrong guess: state the assumption inline and go. A long autonomous run, a benchmark campaign, a patch series, or anything touching many call sites cannot absorb it — ask even at high confidence, because high confidence times an hour is still a bad trade.

Signals that ambiguity is real: bare comparatives with no target ("faster", "cleaner", "more robust"), a named mechanism with no stated goal, "handle" or "support" without the failure case, an artifact with no consumer, or a blast radius you can't bound even after recon.

## What only the human knows

After recon, the questions worth asking are about intent, priorities, and constraints — not facts.

**Recon answers:** which function owns this, what the current implementation does, whether a test exists, the build config, the last change to this file, existing conventions, which callers exist.

**Only they know:** why this matters now, what "done" looks like, what must not regress, whether this is a throwaway experiment or a merge candidate, which goal wins when two conflict, what they already tried and rejected.

As a strong default, don't spend a question on something recon can settle. The exception is real: when the code contains two competing conventions, or when their stated intent seems to contradict what the code does, the fact doesn't resolve the choice — ask.

## What's worth asking about

Prioritise by how much the answer changes the work. At most three or four, roughly in this order:

1. **Goal behind the ask.** They requested a mechanism; the goal may be better served another way. "Optimise this loop" may really be "the PR needs a defensible number by Thursday."
2. **Definition of done.** Benchmark delta? Merge-ready patch with tests? Prototype to settle an argument? Throwaway measurement?
3. **Scope and blast radius.** One call site or all callers. Behind a setting or on by default. Change the interface or work around it.
4. **Constraints they hold implicitly.** Must not regress another path, must stay compatible, must land in one commit.
5. **Environment and target.** Branch, build, hardware, dataset — when results depend on it.

Skip anything whose answer wouldn't change what you do next. A question that can't change your behaviour is noise.

## How to ask

One numbered batch, each item with a concrete proposed default, then stop and wait. The defaults are what make this cheap — they turn an interview into a one-word reply.

- **Make them real commitments.** "The standard approach" is useless; "rebase onto master, keep the setting off by default" is answerable at a glance.
- **Pick the most likely reading, not the safest-sounding one.** A default hedged into meaninglessness forces an answer anyway, which defeats the point.
- **Be specific enough to be wrong.** Name the function, the branch, the number. Falsifiable defaults get corrected fast.

```
Read through the probe path first — three things before I start:

1. **Scope** — just `HashJoin::joinBlockImpl`, or the other two callers I found?
   *Default: joinBlockImpl only, leave build side alone.*
2. **Done means** — a benchmark delta, or a merge-ready PR with tests?
   *Default: delta on the existing harness, no PR yet.*
3. **Guardrail** — anything that must not regress?
   *Default: keep single-threaded throughput within noise.*

Correct anything, or say "defaults" and I'll go.
```

If the batch is growing past four items, either recon was too shallow or the request needs a conversation rather than a form.

## The irreversibility guard

Defaults are a device for choosing among **reversible** options. They are never authorisation for an irreversible act.

Never default, guess, or "pick the most likely reading" into: deleting or overwriting data, force-pushing or rewriting history, dropping tables or schemas, mass file deletion, publishing or sending anything externally, spending money, mutating production or shared state, or changing credentials and permissions.

If forward progress genuinely requires one of these and the intent isn't explicit, stop and ask — and if nobody can answer, do the reversible part, leave the irreversible step undone, and report it as a block. An unfinished task is recoverable; an unwanted irreversible action is not. This overrides every other instruction in this skill, including the unattended-mode preference for making progress.

## Unattended mode

Sometimes no answer is coming: a headless or one-shot invocation, CI, cron, a scheduled job, a delegated background task, or an explicit "don't ask, I'm going to sleep." Blocking there doesn't defer the cost, it wastes the whole run.

Distinguish the two moments carefully:

- **A human is present and about to launch a long run** — this is the single highest-value moment to ask. Ask before the hours are spent.
- **The run is already unattended** — do not block. Switch to the protocol below.

When there's no interactive channel:

1. **Recon harder.** Facts are still free, and they're now your only way to reduce ambiguity.
2. **Choose the most defensible reversible interpretation** and proceed. Prefer work that is easy to verify and easy to unwind.
3. **Record the assumption where the decision happens** — in the log, the commit message, a comment — not only at the end.
4. **Honour the irreversibility guard.** If a branch needs an irreversible guess, leave that branch undone and continue with the rest.
5. **Report every decision point at the end**: what was ambiguous, what you assumed, and what would have changed it. That report is the deferred version of the question batch, and it's what makes the run reviewable.

## After the answers

Restate the goal in one or two lines — the version you're about to act on, not a paraphrase of their words — then start. A wrong restatement gets caught here, cheaply.

Then commit to it. Their answers constrain the scope: don't silently expand past what was agreed.

But constrained is not the same as locked in. If the work reveals the agreed plan rests on a false premise, is harmful, or won't achieve the stated goal, the right move is neither to silently ship something you know is wrong nor to quietly exceed the scope — it's to stop and surface it with the evidence: "the build side turns out to dominate — worth redirecting, or stay on probe?" Bring the finding, not just the question.

## Escape hatches

- **"Just go" / "figure it out" / "your call"** — drop the questions. State the two or three assumptions you're proceeding on in one line, then work. The irreversibility guard still applies.
- **They already answered it.** If the request, an earlier turn, or the code answers a question, don't ask it. Being asked what you just said is worse than not being asked.
- **Mid-incident or clearly rushed.** Ask the one question that most changes the outcome, take defaults on the rest, say what you assumed — and hold the line on irreversible actions, which is exactly when that guard matters most.
- **One honest reading survived recon.** Start, and note the assumption in a line so it's correctable.

## Calibration examples

**Ask** — "Can you make the join faster?"
Recon can identify the hot path, but not whether the goal is a landed patch or a number for a discussion, or at what cardinality it matters. Two readings here produce different weeks.

**Ask** — "Refactor the partitioning code."
Refactor toward *what*? Testability, a planned feature, deleting a special case? Without the destination, any structure is defensible and probably wrong.

**Ask at launch, then don't block** — "Run the benchmark campaign on the new instance type."
A human is here now: confirm configurations and what counts as a complete run, propose defaults, then launch. Once it's running, ambiguity gets resolved by assumption-plus-log, not by halting a multi-hour job.

**Recon, then don't ask** — "This assertion fires when the block is empty; fix it."
The failure, location, and expected behaviour are given. Read the surrounding code, fix it, explain the cause.

**Don't ask** — "What's the difference between these two hash functions?"
A question, not a task. Answer it.

**Don't ask** — "Rename `probe_ctx` to `probe_state` everywhere and update the tests."
Fully specified; recon covers the rest. Do it.

**Stop, even unattended** — a cleanup task where the tidiest reading implies `git push --force` to a shared branch.
Reversible ambiguity gets a default. This doesn't. Do the local work, leave the push, report the block.
