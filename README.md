# sdd

Personal collection of agent skills, slash commands, and templates for **spec-driven development** with Cursor.

## What is this?

A home for reusable agent assets — `SKILL.md` files, slash commands, prompts, and spec templates — that help drive software work from a written specification rather than ad-hoc prompts.

> **Spec-driven development (SDD):** write a precise specification of *what* and *why* first, then have an agent (or yourself) generate, regenerate, and verify the *how*.

The spec is the durable artifact. Code is a (re)generable output.

## Why spec-driven development?

### Advantages

- **Reproducibility.** Regenerate code from the spec instead of re-prompting from scratch. Useful when refactoring, swapping stacks, or porting between languages.
- **Auditable intent.** Reviewers see *why* before *what*. A diff of the spec is easier to reason about than a diff of generated code.
- **Reduced hallucination.** Explicit constraints (inputs, invariants, edge cases) leave agents less room to invent.
- **Better onboarding.** Specs encode rationale; new contributors — human or AI — ramp up faster than they would from code alone.
- **Forces clarity before commitment.** Many "bugs" are unwritten requirements. SDD surfaces them earlier.
- **Composes with TDD.** Tests are a machine-checkable subset of the spec; agents can derive them.
- **Survives context resets.** A persisted spec outlives any single chat, model, or session — agents can resume from it.

### Disadvantages / trade-offs

- **Upfront cost.** Writing a good spec is real work. For one-off scripts or genuine exploration it can be slower than just coding.
- **Over-specification risk.** Rigid specs prematurely lock in design and discourage emergent solutions.
- **Sync drift.** Edit code without updating the spec and the spec rots. Either treat the spec as canonical (regenerate) or invest in tooling to keep both aligned.
- **Skill curve.** Specifying clearly, at the right level of abstraction, is a learnable but non-trivial skill.
- **Lossy abstraction.** Some implementation details (perf tweaks, library quirks, platform bugs) are awkward to express in prose; the spec can't be the *only* source.
- **Tooling immaturity.** Conventions, linters, and round-trip generators for specs are still in flux.
- **Bad fit for spikes.** When you don't yet know what to build, writing a spec is just speculation in fancier clothes.

### Compared to other approaches

| Approach | How SDD differs |
| --- | --- |
| Chat-only / "vibe coding" | Persistent, versioned source of intent; doesn't vanish when the chat ends. |
| Traditional requirements docs | Living and lightweight; iterated alongside the code, not frozen up front. |
| Pure TDD | Captures intent and constraints beyond what's testable; tests fall out of the spec. |
| Issue tickets only | A ticket says "do X"; a spec says what X is, why, and when it's correct. |

### When *not* to use SDD

- True prototyping where the goal is to learn what the right thing is.
- Trivial changes where the diff *is* the spec.
- Throwaway scripts.

## Layout

Planned (populated as patterns emerge):

- `skills/` — `SKILL.md` capability packs for agents.
- `commands/` — Reusable slash commands and prompts.
- `templates/` — Spec templates (feature, refactor, bug, ADR, etc.).
