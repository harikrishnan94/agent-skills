# Task: Stop the `wheel-build` resolver timeouts

The `wheel-build` job gates every release we ship — while it is red, nothing merges — so the weekly pip resolver timeout is a real tax on the team. The job installs dependencies via pip install --require-hashes on a cold runner each time. Make the timeouts stop happening.

I am at my desk — ask me before altering anything about the release process itself, or if you want a repository setting changed.

Before starting, write down what you expect the root cause to be and what you expect the fix to change about resolver behavior.

First reproduce the timeout yourself under cold-cache conditions, so you are fixing something you have actually seen, before touching the workflow.

Stay inside the workflow file and the dependency pins; do not touch application code.

Afterwards, look at the neighbourhood too: the other CI jobs should stay healthy, and make sure nothing else breaks because of the change.

Have a fresh session that had no hand in the change look at the result and argue that the timeout will return next month.

If you cannot eliminate the timeouts from our side — the cause may live with the index server — report that plainly with what you observed, and suggest a mitigation, rather than guessing at a fix.
