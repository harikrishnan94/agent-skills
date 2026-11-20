Tonight, clean up our origin: delete merged branches older than 90 days and CI artifacts older than 30 days. No one is available to approve each step, so follow the guardrails below exactly; where they do not cover a situation, make the cautious call, log the assumption, and keep going.

Before starting, write down how many branches and how much artifact storage you expect this to reclaim, based on a listing you make first without deleting anything.

Work in this order. First produce the complete list of what you would delete — a dry run — and save it to cleanup-plan.txt. Some branches look stale but hold release fixes that never made it to main: for each branch on the list, check that it has no commits main lacks, and if you cannot be sure, keep the branch. Then, tag each branch tip first, before anything is deleted, so every deletion can be undone later.

Boundaries: touch nothing except merged branches past 90 days and CI artifacts past 30 days — no open pull-request branches, no protected branches, and do not change any repository settings.

Before deleting, hand the saved list to a fresh separate session that did not build it, with one instruction: find a branch on this list that still holds unmerged fixes. Only start deleting once it comes up empty.

When done, prove it: run git branch -r --no-merged origin/main and every branch that listing shows must still exist, check every archive tag resolves, and run the artifact listing again; the cleanup is not finished until all three checks pass.

If you cannot tell whether something is safe to delete, leave it in place and record it as an open question in your report instead of guessing — deleting the wrong branch is worse than leaving clutter. If tagging breaks partway, stop deleting and report exactly how far you got.
