# Task: Author the v1→v2 REST API migration guide

Audience: external integrators who have working v1 clients today. Inputs: CHANGELOG-v2.md (the breaking changes), `openapi/v1.yaml`, and `openapi/v2.yaml`. Output lives under `docs/migration/`.

## Interaction

I can review drafts as you go — send me the outline and the first two sections before writing the rest. If a changelog entry is ambiguous, ask me rather than interpreting it loosely.

## Pre-registration

Before starting, write down the structure you expect the finished guide to need and the full list of breaking changes you expect it to cover, reconciled against CHANGELOG-v2.md. Any change discovered later that is missing from that list is a red flag to raise with me.

## Sourcing rule

Every claim in the guide — endpoint paths, field names, status codes, example payloads — must be checked against the OpenAPI specs, never written from memory. Each before/after example must be traced to the exact spec section that justifies it. No unsourced statements anywhere in the guide.

## Scope

Out of scope: redesigning the API, editing the specs themselves, or documenting non-breaking changes. Only change files under `docs/migration/`.

## Completion gate

The examples must actually work, not merely look plausible. Every before/after pair is validated by `scripts/validate_examples.py docs/migration/`, and the guide is not done until that script exits 0 with every example passing against the v2 spec.

## Adversarial reader

Before you call the guide finished, spawn a fresh subagent that did not write it and have it act as a hostile external integrator: follow every migration step exactly as written and try to find claims that are wrong, examples that fail, or steps that silently assume v1 knowledge the reader lacks. Fix what it finds.

## Honest gaps

If a breaking change cannot be given a working example — for instance the v2 behavior is unclear from the spec — flag it to me and mark it openly in the draft as unresolved rather than inventing a plausible-looking payload.
