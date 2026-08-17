# ADR 0002: Event occurrence is separate from Canonical State truth

- Status: Accepted
- Date: 2026-08-17

## Context

Persistent characters need both a record of what happened and a current accepted understanding. Treating conversation history as truth conflates occurrence, evidence, interpretation, correction, and current belief.

## Decision

RelayLM keeps these roles separate:

- Event Journal records occurrence and provenance;
- Canonical State records accepted current understanding;
- Context Compiler selects cognitive material for the current turn without turning prompt residency into truth.

An Event can exist without creating State. Removing or replacing current State does not erase the source Event. Assistant-authored dialogue may support continuity but does not self-certify user or external facts.

## Consequences

- State changes pass through deterministic authority validation.
- Retrieval and Context selection are read/projection concerns, not State mutation.
- Corrections can change current understanding while preserving provenance of the earlier occurrence.
- Persistence and Context residency have distinct lifecycles.
