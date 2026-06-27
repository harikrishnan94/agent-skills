<!-- Append the "## Session state tracking" section below into
     ~/.copilot/copilot-instructions.md (Copilot CLI's global instruction file) to
     complete the session-scratchpad hook. The hook injects the scratchpad path at
     sessionStart; this instruction is the durable INGEST half that tells Copilot to
     treat the file as authoritative (and survives compaction, which sessionStart
     does not re-fire on). -->

## Session state tracking
A per-session scratchpad exists at the scratchpad path injected at session start.
- Update it immediately after completing any step, making any decision, or changing the plan.
- Before starting work after any gap or compaction, re-read it and resume from "Current step".
- Never rely on conversation history for task state; the file is authoritative.
