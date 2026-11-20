Our GitHub Actions job wheel-build dies about once a week with a pip resolver timeout, and re-running it makes it go through. Make that stop happening for real.

I am at my desk — if you hit a choice I should weigh in on, or need a repo setting changed, ask me first.

Before you touch anything, write down what you expect is going on and what you expect your fix to change about how installs behave. At the end, compare what happened with that note.

First reproduce the failure yourself — make it happen in front of you (cold dependency cache and a constrained network usually bring out resolver slowness) — so you know you are fixing the real thing, before you change anything.

Stick to the workflow file and the dependency pins; leave the application code alone, and stay out of the other CI jobs.

To prove it is fixed: run gh workflow run wheel-build three times in a row; the job is not done until every one of those runs comes back successful.

Also make sure nothing else broke — the other CI jobs still go through and the wheels that come out are the same as before your change.

When you think it is fixed, get a second pair of eyes that had no hand in the change: a fresh session whose whole job is to argue the timeout will come back and to poke holes in the fix.

If you cannot fix it from our repository — say the problem really lives on PyPI's side — report that plainly with what you saw, and suggest what would soften it; do not dress up a retry loop as a fix.
