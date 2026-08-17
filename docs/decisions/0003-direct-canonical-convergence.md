# ADR 0003: Direct canonical convergence in v1

- Status: Accepted
- Date: 2026-08-17

## Context

RelayLM v1 is a greenfield product line. Keeping obsolete internal contracts alive through aliases, shims, forwarders, dual reads/writes, or temporary bridges would recreate authority ambiguity and compatibility debt without a current product requirement.

## Decision

One concept has one current owner.

When an internal contract changes, RelayLM changes the canonical owner directly, migrates affected internal consumers in the same bounded transaction, and removes the superseded path.

Compatibility patches, shims, old-path aliases/forwarders, temporary bridges, monkey patches preserving obsolete contracts, dual-read/dual-write migration paths, simultaneous old/new semantic authorities, and deprecated-behavior fallbacks are prohibited by default.

Permanent adapters are allowed at genuine external protocol/provider/storage boundaries when they translate between the current RelayLM contract and an external contract. Any future post-release compatibility requirement must be an explicit versioned compatibility contract.

## Consequences

- Internal breaking changes are resolved by atomic convergence rather than compatibility layering.
- Fresh-head review checks for accidental compatibility accretion.
- Migration machinery is introduced only when an explicit released external contract requires it.
