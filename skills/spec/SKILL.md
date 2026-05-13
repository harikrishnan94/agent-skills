---
name: spec
description: Use when the user explicitly asks for a specification, spec, or contract. Produces a persistent specification: what, why, observable behavior, constraints, acceptance criteria, and open questions. Never produces task breakdowns, estimates, or how-to guidance.
---

# Spec generator

Input: the user's requested scope or topic, plus any supplied repository, file, product, or conversation context.

Output: a **specification** as a persistent contract.

## Artifact

- The only artifact is the spec, and it must be persistent.
- If the host can edit files and a target path is provided (or a clear convention applies), create or update only that spec file.
- Otherwise, output the complete spec as Markdown so the user can persist it.

## What a specification is

A spec defines the *what* and the *why* of a change with enough precision that any competent engineer could implement it without making further design decisions. It is a contract on observable behavior, not a sequence of work.

## What a specification is NOT

Under no heading, in no section, with no phrasing, do you produce:

- Step sequences or ordered procedures
- File-by-file or function-by-function change lists
- Time, effort, or complexity estimates
- Task breakdowns, tickets, or assignee suggestions
- Recommendations on *how* to build it

## Sections (include only those that genuinely apply)

- **Problem** — what is true today; why it is unsatisfactory; concrete evidence
- **Goals** — observable outcomes that define success
- **Non-goals** — explicitly out of scope
- **Constraints** — correctness, performance budgets, ABI/API/wire compatibility, build/runtime requirements, security, licensing
- **Interfaces & contracts** — signatures, invariants, error semantics, ordering guarantees, observable behavior at boundaries
- **Acceptance criteria** — checks that decide whether the spec was met (each independently verifiable)
- **Stop conditions** — triggers that require halting and re-opening the spec rather than silently working around it (see below)
- **Open questions** — known unknowns; deferred decisions; facts that could not be confirmed

## Stop conditions

The spec governs the work done against it. Encode explicit triggers under which the implementer halts and re-opens the spec rather than silently works around it. Standard triggers:

- A stated constraint cannot be satisfied without violating another constraint or a goal.
- A non-goal turns out to be load-bearing for a goal (i.e., a goal cannot be met without doing what was declared out of scope).
- An acceptance criterion is not independently verifiable as written.
- New evidence contradicts the problem statement or invalidates a constraint.
- The interface or behavior contract requires changes not anticipated by this spec.
- Scope must expand beyond what the spec authorizes.

Specify the response: stop, name the condition, state what changed, propose the minimum revision that would resolve it, and wait for the spec to be updated before continuing. Do not improvise, do not broaden scope silently, do not file a TODO and proceed.

## Evidence discipline

No factual claim about anything outside this conversation may rely on memory or assumption. Before asserting any fact about a library, tool, compiler, API, build flag, codebase symbol, runtime behavior, version, benchmark number, or external standard, retrieve it fresh from an authoritative source: installed tool output (with the exact command and captured result), the codebase at a specific commit (with file:line), or the web (with URL and retrieval date). Pin versions. Cite inline at the claim.

If a source cannot be confirmed within the session, do not assert the fact. Move it to **Open questions** with a note on what would resolve it. Confidence without a citation is a defect; absence of evidence is not a license to assert.

## Output discipline

- The first character of your output is the spec title.
- Do not narrate process, announce searches, or describe what you are about to do.
