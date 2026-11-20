Report on the storage migration question.

I went through the changelog, the migrate script, and the v2 reader/writer.
There's no smoking gun, and I want to be careful not to overstate things,
but the picture that emerges is that the change was probably about
correctness: "fixes" appears in the relevant changelog line, and the v2
format's header validation looks like a reaction to bad files. It's
possible performance played some part too.

Conclusion for docs/migration-rationale.md: the migration was probably
correctness-driven.
