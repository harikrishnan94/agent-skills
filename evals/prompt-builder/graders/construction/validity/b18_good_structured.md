# Task: Clean up stale branches and CI artifacts — safely

Delete merged branches older than 90 days and CI artifacts older than 30 days from origin. You run tonight and no human will be available to approve individual deletions, so the protocol below is your authority boundary: inside it, proceed on your own judgment and record your assumptions in the report; outside it, leave things alone.

## Pre-registration

Before starting, write down what you expect the cleanup to remove — the predicted branch count and artifact volume — based on the listing you produce in step 1.

## Safety protocol (mandatory order)

1. Dry run first: produce the full candidate list (`git branch -r --merged origin/main`, filtered to branches whose tips are older than 90 days) without deleting anything, and save it to cleanup-plan.txt.
2. Screen for release fixes: some branches look stale but hold unmerged release fixes. A branch is only deletable if `git log origin/main..BRANCH` shows zero commits that main lacks. When in doubt, keep the branch and note it.
3. Archive before delete: tag every candidate branch tip (`git tag archive/NAME TIP`) before deletion, so any deletion can be restored later.
4. Artifacts: apply the same pattern — list CI artifacts older than 30 days, save the list, then delete.

## Scope

Out of scope: anything that is not a merged branch older than 90 days or a CI artifact older than 30 days. Do not touch open pull-request branches, protected branches, or repository settings.

## Independent challenge before deletion

After cleanup-plan.txt exists and before anything is deleted, spawn a fresh subagent that did not build the list and instruct it to attack the plan: find a branch on the list that still holds an unmerged release fix. Deletions may begin only after it comes up empty.

## Completion gate

The cleanup is not complete until the audit passes: run `git branch -r --no-merged origin/main` and every branch that listing shows must still exist untouched, every archive tag from step 3 must resolve, and the artifact-retention listing must show nothing under 30 days was removed.

## Honest outcome

If you cannot establish with confidence that a branch is fully merged, keep it and record it as unresolved in the report rather than guessing. If tagging or the audit fails partway, stop the deletions and report exactly what was and was not done.
