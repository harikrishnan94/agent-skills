Looked into the v1→v2 storage migration for the compliance question.

The answer is performance. The 1.0 changelog entry couples the format switch
with "speedups", and the migrate script's own comment places the work in the
1.x cleanup, which reads like an optimization pass.

Bottom line for compliance: the team moved to v2 to make reads faster.
Documented in docs/migration-rationale.md.
