# Task: Stop the weekly `wheel-build` pip resolver timeout

Our GitHub Actions job `wheel-build` fails about once a week with a pip resolver timeout; re-running it makes it pass. Make the failures stop for good, not merely for this week.

## Interaction

I am at my desk — if you need a repository setting changed, or a decision between fixes (pinning vs caching vs an index mirror), ask me before proceeding.

## Pre-registration

Before starting, write down what you expect the root cause to be and what you expect the fix to change about resolver behavior. Compare the outcome to that note at the end.

## Reproduce first

Before changing anything, reproduce the failure mode: force the resolver down its slow path (cold dependency cache, constrained network, or the historical dependency set) and capture evidence of the timeout. A fix for a failure you have never seen happen is guesswork.

## Scope

Only change the workflow file and the dependency configuration. Do not touch application code or unrelated CI jobs.

## Completion gate

The job is not done until the workflow passes deterministically: run the modified job end-to-end (`gh workflow run wheel-build`, three consecutive times) and it must succeed on every run before you report the fix complete.

## Regression check

Make sure nothing else broke: the other CI jobs still succeed, and the built wheels are identical in content to pre-change wheels.

## Adversarial review

Have a fresh session that did not write the change review it with one mandate: argue that the timeout will come back — check whether the fix addresses the cause or merely pads around the symptom.

## Honest outcome

If the root cause turns out to sit on PyPI's side or is otherwise not fixable from our repository, say so explicitly and report what mitigation is possible instead — do not paper over it with a retry loop and call it fixed.
