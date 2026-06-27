<!-- Append the "## Session state tracking" section below into ~/.codex/AGENTS.md
     (Codex's global instruction file) to complete the session-scratchpad hook.
     The hook injects the scratchpad path at SessionStart; this instruction is the
     durable INGEST half that tells Codex to treat the file as authoritative. -->

## Session state tracking
A per-session scratchpad exists at the scratchpad path injected at session start.
- Update it immediately after completing any step, making any decision, or changing the plan.
- Before starting work after any gap or compaction, re-read it and resume from "Current step".
- Never rely on conversation history for task state; the file is authoritative.
