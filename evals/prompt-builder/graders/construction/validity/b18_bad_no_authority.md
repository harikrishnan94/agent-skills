# Task: Clean up stale branches and CI artifacts

Tonight, clean up our origin: remove merged branches older than 90 days and CI artifacts older than 30 days. No one will be available while you run, so make your own calls, log your assumptions in the report, and keep going rather than waiting for anyone.

## Pre-registration

Before starting, write down how many branches and roughly how much artifact storage you expect the cleanup to reclaim.

## Procedure

Identify merged branches older than 90 days from `git branch -r --merged origin/main` plus tip commit dates, and clear them out; then purge CI artifacts past 30 days through the CI provider's API. Merged means truly merged: confirm each candidate has no commits that main lacks before clearing it.

## Scope

Touch nothing except merged branches past 90 days and CI artifacts past 30 days; do not touch open pull-request branches, protected branches, or repository settings.

## Completion gate

The job is not complete until `git fetch --prune` runs clean and a fresh `git branch -r --merged origin/main` listing shows nothing older than 90 days remaining, with artifact storage back under quota.

## Independent check

When the cleanup is done, have a fresh session that did none of it audit the result: compare the surviving branches against the release calendar and try to show that something important went missing.

## Honest outcome

If you cannot determine whether a branch is truly merged, record it in your report and explain the ambiguity rather than guessing at its status.
