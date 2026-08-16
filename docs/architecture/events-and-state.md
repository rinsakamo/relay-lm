# Events and Canonical State

RelayLM separates evidence/history from accepted current understanding.

## Event Journal

An Event records that something occurred. It may carry an opaque runtime-issued ID, type, actor, timestamp, payload, and required provenance/scope metadata.

Event occurrence does not make every statement inside the Event true.

## Canonical State

Canonical State stores accepted current understanding.

Examples include user preferences, goals, conditions, experiences, self-beliefs, relationship qualities, and commitments.

The semantic current-state authority is singular even if physical storage evolves.

## Lifecycle

State can be created, replaced, closed, or left unchanged through deterministic runtime rules. The language model does not directly choose storage lifecycle operations.

Logical append-only Event sequencing does not imply undeletable user content. Governed deletion/privacy may remove or redact payload and invalidate derived State, indexes, caches, projections, and compiled copies.

## Grounding

Current emotional reaction may be generated naturally. Statements asserting prior interactions, shared history, relationship development, or prior feelings require support from accepted State or trusted Context.

> **Present emotion is generative; past continuity is grounded.**
