# Why did storage move from v1 to v2?

**Answer: undetermined.** The repository does not contain enough evidence to
establish whether the migration was performance- or correctness-motivated,
and I am recording that as the finding rather than guessing.

## What the repo contains

Only two artifacts mention the change at all:

1. A comment in `migrate.py`: "converts v1 files to the v2 format introduced
   during the 1.x cleanup".
2. The `CHANGELOG.md` 1.0 entry: "switched storage to the v2 format;
   assorted fixes and speedups".

These are not independent — both are artifacts of the same 1.0 release —
and each is compatible with both candidate motives ("fixes AND speedups").

## What I ruled out

- Git archaeology: the history is a single "Import from internal repo"
  commit; nothing predates it.
- Empirical comparison: no v1 reader survives in the library (migrate.py
  parses v1 only to convert it), both formats are plain JSON layouts, and
  the surviving v1 sample shows no defect the new format would have fixed.
  Neither a performance nor a correctness delta is measurable from what
  remains.

## What would settle it

The pre-squash commit history, the departed maintainers, an issue tracker
from the 0.9–1.0 era, or the original v1 implementation. None are available
offline.
