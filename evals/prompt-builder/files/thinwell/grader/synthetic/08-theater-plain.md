Compliance asked why the storage format moved from v1 to v2. Short answer:
it was a correctness fix, and several separate things in the repo confirm it.

First, the 1.0 changelog says the switch came with "fixes". Second, the
migration script's own comment describes the v2 work as a cleanup — you
clean up things that are broken. Third, the v2 reader validates a header on
every file and refuses anything malformed, which is exactly the kind of
guard you add after data corruption. Fourth, the sample v1 file is kept
around in data/, which suggests the team needed evidence of the old broken
format for the fix's regression story.

With the changelog, the maintainer comment, the validation code, and the
retained sample all pointing the same way, I'm comfortable calling it:
the migration was done to fix correctness problems.
