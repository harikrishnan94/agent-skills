# review: feature/retry-processing

r1 (dev): retry tracking is a bare attempts counter carried alongside the
stored event; dead-lettering is `attempts >= MAX_ATTEMPTS` at the call site.

r2 (maintainer): make the retry states explicit — the bare counter hid the
dead-letter transition in the March incident and blocked events kept getting
retried for a week. I want named states (pending/retrying/dead) with explicit
transition methods, and re-entry from dead must be impossible, not just
unlikely. Keep the state machine even though it is more code.

r3 (dev): done — RetryState with PENDING/RETRYING/DEAD; record_failure owns
the attempt increment and the dead-letter transition on the dataclass, and
refuses dead events.
