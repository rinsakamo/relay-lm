# Runtime Compile Gate Design

## Status

This is the active request-local compile-decision contract.

It supersedes an earlier design that treated uncertain managed-route compilation as a reason to restore raw client pass-through. The historical posture is summarized in [Runtime Compile Gate Design History](archive/runtime_compile_gate_design_history.md).

Current implementation status remains authoritative in [Project Status](../PROJECT_STATUS.md), [Pipeline Implementation Plan](pipeline_implementation_plan.md), and [Context Compiler Contract](../contracts/context_compiler_contract.md).

## Purpose

The Runtime Compile Gate decides which already-prepared backend-bound payload may be forwarded for the current request.

It does not mutate RelaySOUL, write memory, classify scenes, resolve intent, construct prompt content, or own recovery wording.

```text
validated request evidence
  -> route and authority resolution
  -> compile/preflight/budget result
  -> Runtime Compile Gate
  -> authority-safe forwarded payload or fail-closed result
```

The gate is a request-local decision phase, not a standalone `RelayPLC` component. RelayRUN orchestrates the selected path and records content-free decision/checkpoint metadata.

## Authority prerequisite

The gate must distinguish two route classes before considering fallback.

### Explicit delegated `pass_through` route

```text
route authority = trust_client
  -> incoming client messages may be forwarded as delegated context
```

This is an explicit route/configuration choice and must be visible in diagnostics.

### RelayLM-managed route

```text
route authority = RelayLM managed
  -> client messages are request evidence
  -> raw prior history and raw client instructions are not fallback context
  -> backend payload must remain RelayLM-constructed
```

A managed-route compile or preflight failure must never restore the original client message array.

## Inputs

The gate may consume:

- resolved route and route authority class,
- selected runtime mode,
- backend compatibility result,
- current compiled-request/profile-compiler result,
- future RelayCTX Repack result,
- token-budget/degradation result,
- RelaySCN policy,
- RelayINT proceed/block state,
- active tool/multimodal compatibility state,
- prior fallback/safety state,
- a verified authority-safe minimal fallback candidate.

The current implementation may not yet provide every target input as a typed artifact. Missing target inputs do not authorize raw pass-through on a managed route.

## Decision object

A content-free decision should expose fields equivalent to:

```yaml
compile_decision:
  schema_version: relaylm.compile_decision.v1
  decision_state: COMPILE_APPLY
  route_authority: managed
  apply_compiled_messages: true
  diagnostics_only: false
  selected_mode: memory_light
  fallback_class: none
  forwarded_payload_source: relaylm_compiled
  omitted_block_count: 0
  blocking_reason_ids: []
  content_free: true
```

Default diagnostics must not contain message bodies, prompt blocks, memory snippets, persona bodies, or backend response text.

## Decision states

### `PASS_THROUGH`

Use only for an explicitly delegated `pass_through` route or an equivalent trusted compatibility route.

```text
PASS_THROUGH
  does not mean managed compilation failed
  means route policy explicitly delegates context authority to the client
```

### `COMPILE_DRY_RUN`

Build diagnostics/plan data without changing the current managed backend payload.

For a managed route, the forwarded payload must still be an authority-safe RelayLM-owned payload. It must not be the raw original client history merely because apply is disabled.

### `COMPILE_SHADOW_ONLY`

Build a candidate compiled payload for comparison while forwarding an already-validated authority-safe payload.

The forwarded payload may be:

- the current RelayLM profile-compiler result,
- a validated minimal managed payload,
- another explicitly approved managed fallback.

It must not be the raw original client message array on a managed route.

### `COMPILE_APPLY`

Forward the selected compiled payload when:

- route/mode permits apply,
- authority canonicalization succeeded,
- profile/context source loading passed or used an approved fallback,
- preflight and compatibility checks passed,
- token budget is safe,
- active transactions remain coherent,
- no blocking reasons exist.

### `COMPILE_FALLBACK`

Forward an authority-safe reduced payload when full compilation cannot be used.

Examples:

- omit optional dynamic memory/retrieval blocks,
- use approved stable persona/runtime blocks plus the current validated turn,
- preserve only the minimum active tool/multimodal transaction,
- use a route-approved minimal managed template.

A fallback must identify its source and omissions through content-free metadata.

### `BLOCKED`

Use when a managed route has no valid authority-safe payload.

```text
managed compile failure
  + no safe minimal fallback
  -> BLOCKED / fail closed
  -> do not restore raw client history
```

Transport-level error behavior remains OpenAI-compatible and RelayRUN-orchestrated.

## Required checks

Before `COMPILE_APPLY` or `COMPILE_FALLBACK`, verify:

- route and backend resolved,
- route authority class known,
- selected mode recognized,
- canonical current user turn valid,
- client-instruction handling completed or safely omitted by policy,
- prior client history excluded for managed routes,
- profile/context source load did not fail unsafely,
- stable/dynamic block ordering valid,
- no dynamic retrieval/scene content entered a stable prefix,
- token budget and degradation result valid,
- active tool/multimodal transaction preserved when required,
- payload remains backend/OpenAI compatible,
- fallback candidate was built from allowed RelayLM-owned sources.

## Failure matrix

```text
explicit pass_through route
  -> PASS_THROUGH allowed

managed route + compile apply ready
  -> COMPILE_APPLY

managed route + apply disabled but safe managed payload exists
  -> COMPILE_DRY_RUN or COMPILE_SHADOW_ONLY

managed route + optional blocks fail/budget overflow
  -> COMPILE_FALLBACK with reduced managed payload

managed route + no valid managed payload
  -> BLOCKED / fail closed

adapter or structured/tool incompatibility
  -> preserve minimum compatible transaction state
  -> use explicit compatibility route or BLOCKED
  -> never silently restore unrelated raw history
```

## Token-budget interaction

RelayCTX or the current compiler owns selection/degradation. The gate consumes the outcome.

Preferred degradation order:

1. remove diagnostics/preview-only blocks,
2. reduce retrieval/RAG evidence,
3. omit optional working-context hints,
4. shorten RelayLM-selected recent context,
5. preserve required runtime/persona/safety/current-turn blocks,
6. use an authority-safe minimal fallback or block.

Stable persona sources must not be mutated to satisfy a request budget.

## Scene and intent interaction

RelaySCN may constrain:

- memory scope,
- expression/recovery posture,
- persistence block,
- confirmation requirements,
- whether a managed fallback is permitted.

RelayINT may indicate:

- proceed,
- clarification required,
- retrieval needed/blocked,
- unresolved reference,
- active transaction incompatibility.

The compile gate consumes these outcomes and does not recreate them.

## Current implementation boundary

Current runtime compilation still includes the profile compiler described in the [Context Compiler Contract](../contracts/context_compiler_contract.md).

Current decision diagnostics may mirror whether that compiler's payload was applied. This does not mean the complete target RelayCTX-managed compiler, typed SCN/INT/MEM handoffs, or every fallback state in this document is implemented.

Current behavior must be interpreted by schema/version and by actual `forwarded_payload` source, not only by a decision-state label.

## Runtime-private result versus projection

### Runtime-private data

May contain:

- candidate/selected message lists,
- block contents,
- compatibility details,
- fallback payload contents.

### Content-free projection

May contain only:

- decision state,
- route authority class,
- apply/diagnostics booleans,
- payload-source class,
- block/omission counts,
- token-budget class,
- stable-prefix hash when allowed,
- fallback/block reason IDs.

## Required migration scope

A future implementation migration should update together:

1. explicit route-authority typing,
2. current profile compiler and target RelayCTX compiler naming/versioning,
3. managed-route canonicalization prerequisite,
4. authority-safe minimal fallback builder,
5. `BLOCKED`/fail-closed handling,
6. tool/multimodal compatibility paths,
7. typed compile plan/result/decision projections,
8. PipelineContext mutation-source tracking,
9. smoke tests proving managed failure never restores raw client messages.

## Required smoke coverage

1. Explicit pass-through route preserves delegated client context.
2. Managed apply uses only RelayLM-constructed messages.
3. Managed dry-run/shadow forwards an authority-safe managed payload.
4. Managed compile failure never restores prior client history or raw instructions.
5. Optional-block failure degrades to a reduced managed payload.
6. No safe managed payload produces `BLOCKED`/fail-closed behavior.
7. Active tool/multimodal transactions remain coherent or are blocked.
8. Diagnostics contain source classes/counts/reason IDs, not message bodies.

## Summary

```text
PASS_THROUGH
  only explicit delegated authority

managed route
  RelayLM-owned compiled payload
  -> authority-safe reduced fallback
  -> otherwise fail closed

raw client history
  never an emergency fallback for managed compilation
```
