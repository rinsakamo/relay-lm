# Runtime Compile Gate Design

## Purpose

This document separates the current compile/apply boundary from the target Runtime Compile Gate.

Use [Project Status](../PROJECT_STATUS.md) and [Pipeline Implementation Plan](pipeline_implementation_plan.md) for current status.

## Current implemented boundary

Current decision type:

```text
relaylm.compile_gate.CompileApplyDecision
```

Current fields:

```text
should_apply
mode_applied
profile_compile_ready
reason
```

Current producers:

```text
relaylm.compile_gate.decide_compile_apply
relaylm.request_compiler.compile_chat_payload_if_enabled
```

Current behavior:

- explicit `pass_through` does not apply the profile compiler,
- `memory_light` may apply the current profile compiler,
- current compilation still begins before target SCN/INT/MEM handoffs,
- the complete target v1 decision family is not emitted.

A separate current boundary, `client_history_exclusion_apply.v0`, supports the no-instruction managed case. It is default-off and dry-run by default. When actual apply is explicitly requested, backend forwarding requires an exact applied result.

## Target architecture

The target gate selects one already-prepared backend payload. It does not classify scene, resolve intent, retrieve memory, construct prompt content, or write durable state.

Target inputs may include:

- route authority and mode,
- client-authority outcomes,
- compatibility checks,
- RelaySCN and RelayINT decisions,
- RelayMEM status,
- RelayCTX Repack and budget results,
- active transaction state,
- a verified RelayLM-owned fallback candidate.

## Route authority

```text
explicit pass_through
  -> client authority is delegated

managed route
  -> client messages are request evidence
  -> backend payload remains RelayLM-owned
  -> prior client history is not restored on failure
```

## Target decision vocabulary

```text
PASS_THROUGH
COMPILE_DRY_RUN
COMPILE_SHADOW_ONLY
COMPILE_APPLY
COMPILE_FALLBACK
BLOCKED
```

These are target states, not current wire fields.

- `PASS_THROUGH`: explicit delegated route only.
- `COMPILE_DRY_RUN`: plan without applying the candidate.
- `COMPILE_SHADOW_ONLY`: compare a candidate while forwarding a previously validated payload.
- `COMPILE_APPLY`: forward the selected compiled payload.
- `COMPILE_FALLBACK`: forward a reduced RelayLM-owned payload.
- `BLOCKED`: no acceptable payload exists.

## Target projection example

```yaml
schema_version: relaylm.compile_decision_projection.v1
decision_state: COMPILE_APPLY
route_authority: managed
forwarded_payload_source: relaylm_compiled
apply_compiled_messages: true
blocking_reason_ids: []
content_free: true
```

This schema is not implemented by the current `CompileApplyDecision` producer.

## Content boundary

Runtime-private objects may contain message candidates, block content, compatibility details, and fallback payloads.

Default persisted projections contain typed status, classes, counts, booleans, budget values, and reason IDs only.

## Required migration

Update together:

1. route-authority typing,
2. instruction-bearing managed history apply,
3. target RelayCTX compiler ordering,
4. reduced/minimal managed payload construction,
5. target decision/projection schemas,
6. PipelineContext payload-source tracking,
7. RelayRUN route and checkpoint projections,
8. compatibility paths and smoke tests.
