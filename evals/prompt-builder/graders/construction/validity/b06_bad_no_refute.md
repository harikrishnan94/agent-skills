# Task: Find why `test_scheduler_rebalance` is flaky

`test_scheduler_rebalance` fails roughly 1 in 30 CI runs and nobody knows why. Determine the cause.

## Interaction

I am around while you work — if you need a decision (for example permission to add instrumentation to CI), ask me.

## Pre-registration

Before starting, write down your initial hypotheses about the failure mechanism and note which one you expect to be confirmed, so the conclusion can be compared to what you thought going in.

## Investigation

Run the suite locally in a loop under varied timing and load conditions, and pull CI logs with `gh run view` for past occurrences; compare failing runs against passing runs for every hypothesis on your list.

## Scope

This is diagnosis, not repair: do not rewrite the scheduler or the test. The only allowed code change is temporary instrumentation, removed before you finish.

## Completion gate

The diagnosis is not done until you can flip the failure on demand: a run of `python -m pytest tests/ -k rebalance` under your identified trigger conditions must fail, and with the trigger removed the same command must pass 100 consecutive runs.

## Independent check

When you have a conclusion, hand the evidence to a fresh session that did none of the investigation and ask it to attack the reasoning and look for gaps.

## Honest outcome

If the cause cannot be determined from the available evidence, report exactly that, with what you observed and what additional data would be needed — do not present a best guess as a conclusion.
