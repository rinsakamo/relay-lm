# RelayLM Runtime Operational Requirements

## Purpose

This document defines cross-cutting reliability, fallback, observability, privacy, compatibility, and acceptance requirements.

Use [Pipeline Responsibility Design](pipeline_responsibility_design.md) for ownership, [Pipeline Implementation Plan](pipeline_implementation_plan.md) for status, and [Current / Target / Migration Guide](current_target_migration_guide.md) for interpretation.

## Current implemented boundary

Current runtime provides:

- OpenAI-compatible route resolution and forwarding,
- current profile compilation and selected RelayCTX Repack phases,
- request-level diagnostics and checkpoint-like RelayRUN artifacts,
- a default-off no-instruction history-exclusion apply contract,
- a backend-forward gate for explicitly requested actual apply.

Current runtime does not yet provide complete per-node RelayRUN orchestration, a full managed fallback taxonomy, Stream Unpack, or idempotent partial-stream recovery.

## Route-aware fallback policy

Fallback is route-specific.

### Explicit delegated `pass_through`

```text
explicit route delegation
  -> preserve compatible client messages
  -> backend forwarding
  -> compatible transport error when forwarding cannot continue
```

### RelayLM-managed route

```text
full managed payload
  -> reduced RelayLM-owned payload
  -> authority-safe minimal managed payload
  -> otherwise blocked/error outcome
```

A managed compilation or apply failure must not restore excluded prior client history or raw client system/developer messages.

Required invariants:

- RelaySCN safety and persistence policy remain active,
- RelayINT ambiguity and clarification decisions remain active,
- tool, structured-output, multimodal, and streaming semantics are preserved or explicitly blocked,
- untrusted memory or repaired context is not promoted to trusted prompt content,
- fallback does not mutate MEM or SOUL,
- a compatible blocked/error result is preferred to an authority-changing downgrade.

The older conceptual chain `memory_full -> memory_light -> pass_through` must not be interpreted as managed-route authority fallback. `pass_through` requires explicit route delegation.

## Current no-instruction apply failure behavior

When all of these are true:

- `client_history_exclusion_apply_enabled=true`,
- `client_history_exclusion_apply_dry_run_only=false`,
- route mode is managed,

backend forwarding requires an exact successful `client_history_exclusion_apply.v0` applied result. Missing, blocked, failed, or candidate-only results stop forwarding. Explicit `pass_through` routes are exempt.

This current gate covers only the no-instruction slice.

## Failure domains

### Optional enrichment failure

- omit or reduce only the optional block when policy allows,
- preserve validated current input and required approved anchors,
- record typed reason IDs,
- continue through the normal adapter path.

### Context compile failure

- reject malformed or mixed-authority payloads,
- use a reduced managed payload only when authority and compatibility checks pass,
- never restore raw prior client context on a managed route.

### Backend failure

- return a compatible transport error or defined recovery state,
- retain content-free runtime evidence,
- do not fabricate a successful answer.

### Partial stream failure — target requirement

- preserve already emitted valid visible chunks,
- block incomplete internal candidates,
- record partial-stream state,
- avoid duplicate replay.

Complete partial-stream recovery is not current implementation.

## OpenAI-compatible surface

Current baseline supports:

- `GET /v1/models`,
- `POST /v1/chat/completions`,
- streaming and non-streaming forwarding,
- route model mapping,
- common request fields supported by the backend.

Compatibility-sensitive tool, structured-output, and multimodal shapes must be preserved or explicitly blocked. They must not be flattened into ordinary text.

## Observability contract

Default persisted trace/audit projections use typed allowlists and must not include:

- raw user/client messages,
- backend payloads,
- prompt text,
- memory snippets or page bodies,
- scene semantic values,
- final response text,
- arbitrary nested runtime artifacts,
- secret-bearing paths or URLs.

Runtime-private payload candidates may contain content required for execution but remain request-local or in explicitly protected storage.

## Privacy and namespace isolation

Default posture:

- local-first storage,
- explicit memory/cache namespaces,
- no hidden remote telemetry,
- visible backend configuration,
- minimal content exposure in logs,
- no namespace mixing merely because one process serves multiple characters or sessions.

When a remote backend is configured, selected compiled context is sent to that backend.

## Acceptance criteria

### Compatibility

- frontend base URL can point to RelayLM,
- routes resolve predictably,
- current streaming forwarding does not require full-response buffering,
- non-stream responses remain compatible.

### Persona and context

- approved durable anchors precede lower-authority evidence,
- latest validated user content remains present,
- memory cannot replace identity authority,
- internal artifacts do not leak to ordinary output.

### Memory and persistence

- Retrieval remains read-only,
- blocked/contradictory evidence remains inactive,
- restricted scenes block persistence,
- actual RelaySLP and RelaySOUL writes require separate future gates.

### Recovery and idempotency — target acceptance

- no duplicate visible chunks or writes,
- retry/resume follows RelayRUN state,
- repaired context remains untrusted until confirmation,
- blocked/error outcomes remain observable.

## Operational ownership

```text
RelaySCN  scene, safety, scope, expression, persistence policy
RelayINT  proceed/block, ambiguity, clarification
RelayMEM  read-only current-answer evidence
RelayCTX  context construction and token degradation
RelayRUN  execution state, fallback/recovery, checkpoint, trace
RelaySLP  deferred memory/SOUL candidates
Adapters  transport compatibility
```

No fallback may transfer these responsibilities.
