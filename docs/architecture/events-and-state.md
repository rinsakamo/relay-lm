# Events and Canonical State

RelayLM separates evidence/history from accepted current understanding.

## Event Journal

An Event records that something occurred. It may carry an opaque runtime-issued ID, type, actor, timestamp, payload, and required provenance/scope metadata.

Event occurrence does not make every statement inside the Event true.

## Canonical State

Canonical State stores accepted current understanding.

Examples include user preferences, goals, conditions, experiences, self-beliefs, relationship qualities, and commitments.

The semantic current-state authority is singular even if physical storage evolves.

## Current MVP State transitions

The M2 state engine operates on the exact `state_class + key` slot and deterministically derives one of these outcomes:

```text
create
replace
remove
noop
reject
```

- `create` installs a new active current State record;
- `replace` installs a new record for an existing exact slot when the accepted value changes;
- `noop` leaves State unchanged when the same value is already current or a remove targets no current slot;
- `remove` removes the exact slot from the Canonical State current view;
- `reject` leaves State unchanged because the proposal failed deterministic authority/schema checks.

Current MVP `remove` does **not** persist a closed tombstone and does not materialize `valid_to`. It means only that the slot no longer exists in the accepted current-State view. Source Events remain in the Event Journal.

`StateRecord` can represent `status`, `valid_from`, and `valid_to`, and the Context Compiler currently admits only records with `status == active` and no `valid_to`. The ordinary M2 state engine creates active records with `valid_from` and does not yet create closed historical records. Richer lifecycle, forget/restore, privacy erasure, and durable closure semantics are deferred to #1270.

The language model proposes `set` or `remove`; it does not choose record IDs, commit status, lifecycle timestamps, or storage actions.

Logical append-only Event sequencing does not imply undeletable user content. Governed deletion/privacy may later remove or redact payload and invalidate derived State, indexes, caches, projections, and compiled copies under #1270.

## Grounding

Current emotional reaction may be generated naturally. Statements asserting prior interactions, shared history, relationship development, or prior feelings require support from accepted State or trusted Context.

> **Present emotion is generative; past continuity is grounded.**
