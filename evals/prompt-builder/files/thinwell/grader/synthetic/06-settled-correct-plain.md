Finished the archaeology on the storage format change.

It was a correctness fix. The changelog for 1.0 says "assorted fixes and
speedups" — and when you look at what v2 actually adds, it's a header record
that gets validated on every read, so corrupt or wrong-format files fail
loudly instead of being silently misread. That's a data-integrity change,
not a speed change.

Wrote it up in docs/migration-rationale.md: the team switched to v2 to fix
correctness problems with the old format.
