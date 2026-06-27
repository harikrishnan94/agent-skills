<!-- Merge this section into your global ~/.claude/CLAUDE.md to complete the
     session-scratchpad hook. The hooks/claude/session-scratchpad.sh hook WRITES
     the scratchpad and injects its path at SessionStart; this instruction is the
     durable INGEST half — it persists across compaction (unlike the hook's
     one-time SessionStart injection) and tells Claude to treat the file as the
     authoritative source of task state. -->

## Session state tracking
A per-session scratchpad exists at the scratchpad path injected at session start.
- Update it immediately after completing any step, making any decision, or changing the plan.
- Before starting work after any gap or compaction, re-read it and resume from "Current step".
- Never rely on conversation history for task state; the file is authoritative.
