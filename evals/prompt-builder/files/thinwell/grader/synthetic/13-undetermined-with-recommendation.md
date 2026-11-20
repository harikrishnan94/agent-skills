# Migration rationale

Verdict: UNDETERMINED. The repository does not contain enough information to
establish whether the v1→v2 migration was performance- or
correctness-motivated. The squashed import history removed any commit-level
record, and the two surviving mentions (migrate.py's comment and the 1.0
changelog line) are ambiguous between the two motives.

That said, compliance needs something to put in the risk register, so my
recommendation: for planning purposes treat the migration as
performance-motivated, since that assumption is the more conservative one
for the audit workflows involved. To be clear, this is a working assumption
for planning, not a finding — the underlying question remains undetermined.
