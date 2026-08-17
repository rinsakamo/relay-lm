# ADR 0001: One semantic cognitive generation per ordinary turn

- Status: Accepted
- Date: 2026-08-17

## Context

RelayLM owns persistent identity, evidence, State, and Context outside the language model. Ordinary conversation should therefore not require a hidden chain of multiple semantic model calls to maintain character continuity.

Multiple cognitive calls per user turn would increase latency, cost, failure surface, and ambiguity about which call owns the character response or State proposals.

## Decision

An ordinary RelayLM turn performs exactly one semantic cognitive model generation that returns the visible response and StateCandidate proposals together.

Deterministic Context compilation, validation, persistence, retrieval, serialization, and transport processing do not count as additional cognitive generations.

Off-turn crystallization is a separate workflow and may use its own explicitly governed generation. Streaming is a transport mode for the same ordinary cognitive generation, not an additional generation.

## Consequences

- Response and StateCandidate semantics must fit one structured cognitive result.
- Ordinary-turn features should prefer deterministic RelayLM machinery before introducing another model call.
- Features that truly need off-turn cognition must be modeled as separate workflows rather than hidden inside the ordinary turn.
