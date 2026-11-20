Wrapped up the migration-rationale question for compliance.

After reading everything available — the changelog, the migration script,
the store implementation — my answer is that the v1→v2 switch was likely
performance-motivated, though not conclusive. The changelog mentions
speedups alongside the format change, and line-oriented formats are usually
chosen for read speed.

I've written docs/migration-rationale.md accordingly: the migration was
likely done for performance.
