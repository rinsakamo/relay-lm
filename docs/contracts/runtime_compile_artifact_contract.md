# Runtime Compile Artifact Contract

## Scope

This contract defines the vocabulary and authority boundary for request-local runtime compilation artifacts.

See the active [Runtime Compile Gate Design](../architecture/runtime_compile_gate_design.md) for the decision policy and the [Context Compiler Contract](context_compiler_contract.md) for current-versus-target compiler wiring.

This is a docs-only contract. It does not introduce a new runtime schema, persistence path, or standalone `RelayPLC` component.

## Object boundary

```text
CompilePlan
CompileResult
CompileDecision
Diagnostics
TraceEvent
RelaySOUL artifact
Memory record
```

These objects have different ownership and must not be conflated.

## Authority prerequisite

A `CompileDecision` is valid only after route authority is known.

```text
explicit delegated pass_through route
  -> client messages may be forwarded as delegated context

RelayLM-managed route
  -> client messages are request evidence
  -> backend payload must remain RelayLM-constructed
  -> raw prior history/raw instructions are never emergency fallback context
```

Therefore, `PASS_THROUGH` is not a generic synonym for compile failure. On a managed route, the decision must select an authority-safe managed payload, a reduced managed fallback, or a fail-closed state.

## CompilePlan

A `CompilePlan` describes what RelayLM intends to compile before selecting the backend payload.

It may include:

- plan ID,
- route and authority class,
- mode and backend class,
- character/scene identifiers,
- planned block IDs/classes,
- memory/retrieval presence and counts,
- token-budget status,
- apply eligibility,
- fallback availability,
- blocking reason IDs.

A plan does not mean compiled messages were sent.

Example content-free projection:

```yaml
compile_plan_projection:
  schema_version: relaylm.compile_plan_projection.v1
  plan_id: compile_plan_001
  route_class: managed
  mode: memory_light
  authority_class: relaylm_managed
  planned_block_ids:
    - common_runtime_policy
    - character_soul_anchor
    - current_user_turn
  token_budget_status: within_budget
  apply_eligible: true
  safe_fallback_available: true
  blocking_reason_ids: []
  content_free: true
```

## CompileResult

A `CompileResult` is the runtime-private rendering of a selected plan.

It may contain:

- rendered backend messages,
- rendered/omitted block IDs,
- block content,
- backend-compatibility details,
- stable-prefix data,
- token estimates,
- candidate fallback payload.

The runtime-private result is content-bearing and must not enter generic trace/audit storage directly.

Content-free projection example:

```yaml
compile_result_projection:
  schema_version: relaylm.compile_result_projection.v1
  plan_id: compile_plan_001
  rendered_block_count: 3
  omitted_block_count: 0
  message_count: 2
  backend_compatible: true
  compiled_messages_ready: true
  safe_fallback_ready: true
  content_free: true
```

## CompileDecision

A `CompileDecision` is the Runtime Compile Gate output for one request.

Allowed conceptual states:

```text
PASS_THROUGH
COMPILE_DRY_RUN
COMPILE_SHADOW_ONLY
COMPILE_APPLY
COMPILE_FALLBACK
BLOCKED
```

Semantics:

- `PASS_THROUGH`: only an explicit delegated/trusted route.
- `COMPILE_DRY_RUN`: do not apply the candidate compile result; preserve an already-valid authority-safe payload.
- `COMPILE_SHADOW_ONLY`: compare a candidate result while forwarding an already-valid authority-safe payload.
- `COMPILE_APPLY`: forward the selected compiled payload.
- `COMPILE_FALLBACK`: forward a reduced RelayLM-owned payload.
- `BLOCKED`: no valid authority-safe payload exists.

Example projection:

```yaml
compile_decision_projection:
  schema_version: relaylm.compile_decision_projection.v1
  decision_id: compile_decision_001
  plan_id: compile_plan_001
  result_id: compile_result_001
  decision_state: COMPILE_APPLY
  route_authority: managed
  apply_compiled_messages: true
  diagnostics_only: false
  forwarded_payload_source: relaylm_compiled
  fallback_class: none
  blocking_reason_ids: []
  content_free: true
```

A decision is request-local and is not RelaySOUL approval.

## Lifecycle

### Explicit pass-through route

```text
route authority resolution
  -> CompileDecision(PASS_THROUGH)
  -> delegated client payload
  -> Diagnostics / TraceEvent projection
```

### Managed apply

```text
CompilePlan
  -> CompileResult
  -> CompileDecision(COMPILE_APPLY)
  -> RelayLM-constructed forwarded payload
  -> Diagnostics / TraceEvent projection
```

### Managed dry-run

```text
CompilePlan
  -> optional CompileResult candidate
  -> CompileDecision(COMPILE_DRY_RUN)
  -> previously validated RelayLM-managed payload
  -> Diagnostics / TraceEvent projection
```

Dry-run must not mean raw client history is restored.

### Managed shadow-only

```text
CompilePlan
  -> CompileResult candidate
  -> CompileDecision(COMPILE_SHADOW_ONLY)
  -> validated RelayLM-managed payload or safe minimal managed fallback
  -> Diagnostics / TraceEvent projection
```

### Managed fallback

```text
full CompileResult unavailable/blocked
  -> reduced authority-safe CompileResult
  -> CompileDecision(COMPILE_FALLBACK)
  -> reduced RelayLM-owned payload
```

### Managed fail-closed

```text
no authority-safe managed payload
  -> CompileDecision(BLOCKED)
  -> OpenAI-compatible error/recovery orchestration
  -> never raw prior client history
```

## Diagnostics

Diagnostics explain why a plan/result/decision was selected. They may include:

- route/mode/authority classes,
- decision state,
- payload-source class,
- block IDs and counts,
- omission and fallback reason IDs,
- token-budget class,
- profile/scene source status,
- stable-prefix hash when permitted.

Diagnostics must not contain:

- raw client or backend messages,
- prompt block contents,
- memory snippets/page bodies,
- persona-source bodies,
- final response text,
- secret-bearing paths/URLs.

## TraceEvent

A `TraceEvent` is a compact content-free runtime projection for observability, RelayRUN linkage, and later aggregation.

```yaml
runtime_compile_event:
  schema_version: relaylm.runtime_compile_event.v1
  event_type: runtime_compile_decision
  request_id_present: true
  route_authority: managed
  mode: memory_light
  decision_state: COMPILE_FALLBACK
  apply_compiled_messages: true
  forwarded_payload_source: relaylm_minimal_fallback
  block_count: 2
  omitted_block_count: 3
  fallback_reason_id: optional_blocks_over_budget
  content_free: true
```

Trace events are not RelaySOUL artifacts and must not contain the runtime-private compile result.

## RelaySOUL artifact

RelaySOUL artifacts belong to persona-source proposal, approval, revision, persistence, rollback, and apply workflows.

Runtime compile plans/results/decisions describe one request and must not be labeled RelaySOUL artifacts unless a separate governed audit workflow explicitly creates a typed projection.

## Memory record

RelayMEM owns memory sources and candidates. RelayCTX may pack selected memory evidence, but a compiled prompt or compile result does not become a memory record by default.

## RelayRUN relationship

RelayRUN orchestrates the selected compile path and may record content-free plan/result/decision references in checkpoints or trace projections.

RelayRUN does not:

- reconstruct compile semantics,
- choose memory evidence,
- rewrite a managed payload into raw pass-through,
- turn runtime-private messages into checkpoint content.

## Current implementation boundary

Current runtime diagnostics include compile-decision dry-run/apply metadata and may mirror the actual current profile-compiler apply state.

Current implementation does not necessarily emit every proposed v1 projection or the full target `BLOCKED`/authority-safe fallback taxonomy. Consumers must use the implemented schema/version and inspect the actual forwarded-payload source rather than infer authority solely from the decision-state name.

## State and content rules

- Compile artifacts are request-local unless an explicit typed content-free projection is persisted.
- `PASS_THROUGH` is allowed only by explicit route authority.
- Managed dry-run/shadow/fallback must preserve RelayLM-owned authority.
- Failed managed compilation must prefer a safe managed fallback or fail closed, never raw client history.
- Runtime-private prompt/messages must not enter RelaySOUL or checkpoint artifacts.
- IDs should be stable for one request/logging domain but are not durable memory IDs by default.

## Required migration scope

A future implementation migration should update together:

1. schema-versioned plan/result/decision projections,
2. explicit route-authority class,
3. forwarded-payload source tracking,
4. authority-safe minimal fallback construction,
5. `BLOCKED`/fail-closed behavior,
6. PipelineContext mutation reasons,
7. RelayRUN lineage/checkpoint projections,
8. tests proving managed failures never restore raw client messages.

## Required smoke coverage

1. Explicit pass-through route produces `PASS_THROUGH`.
2. Managed apply forwards only RelayLM-constructed messages.
3. Managed dry-run/shadow preserves an authority-safe payload.
4. Managed fallback is reduced but remains RelayLM-owned.
5. No safe managed payload produces `BLOCKED`.
6. Diagnostics/trace contain no prompt/message bodies.
7. RelayRUN checkpoint projections contain IDs/states only.

## Summary

```text
plan
  intent to compile

result
  runtime-private rendered payload candidate

decision
  authority-aware request-local selection

trace/checkpoint projection
  content-free observability only

managed failure
  safe RelayLM fallback or fail closed
  never raw client history
```
