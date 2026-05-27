# Runtime Compile Artifact Contract

## Scope

This document defines terminology boundaries for runtime compile artifacts in RelayLM.

It separates these concepts:

```text
CompilePlan
CompileResult
CompileDecision
Diagnostics
TraceEvent
RelaySOUL artifact
Memory record
```

This is a docs-only contract. It does not introduce runtime schema changes or persistence behavior.

## Motivation

RelayLM now has design docs for the Safe SOUL / Scene / CTX compile chain and the Runtime Compile Gate. As implementation grows, words like plan, result, diagnostics, trace, artifact, and decision can become ambiguous.

This document fixes the vocabulary before adding more runtime implementation.

## Object definitions

### CompilePlan

A `CompilePlan` describes what RelayLM intends to compile before changing the outbound backend payload.

It should capture route, mode, character, scene, planned block IDs, memory candidate summary, token budget status, apply eligibility, and blocking reasons.

A plan may be produced for dry-run, shadow-only, fallback, or apply paths. It does not mean compiled messages were sent to the backend.

### CompileResult

A `CompileResult` is the rendered result of a selected plan.

It should capture rendered block IDs, omitted block IDs, message count, backend compatibility, and whether compiled messages are ready.

A result can exist even when the Runtime Compile Gate chooses shadow-only or fallback.

### CompileDecision

A `CompileDecision` is the Runtime Compile Gate output for the current request.

It should capture decision state, whether compiled messages are applied, whether diagnostics-only mode is active, fallback reason, and blocking reasons.

Suggested states:

```text
PASS_THROUGH
COMPILE_DRY_RUN
COMPILE_SHADOW_ONLY
COMPILE_APPLY
COMPILE_FALLBACK
```

A compile decision is request-local. It is not a RelaySOUL approval decision.

### Diagnostics

Diagnostics are human-readable explanations attached to a plan, result, or decision.

They should explain selected route, mode, character, scene, block order, omitted blocks, fallback reasons, token budget status, profile loading status, and scene normalization status.

Diagnostics must not be inserted into stable prompt prefixes by default.

### TraceEvent

A `TraceEvent` is a compact machine-readable runtime event for logs, aggregation, debugging, or future RelayTRC lineage.

Trace events should prefer IDs, states, counters, hashes, and reason codes. They are not RelaySOUL artifacts unless explicitly promoted by a future audit workflow.

### RelaySOUL artifact

A RelaySOUL artifact is an audit object in persona-source patch, approval, revision, persistence, rollback, or apply workflows.

Runtime compile plans, results, decisions, diagnostics, and trace events should not be called RelaySOUL artifacts by default.

### Memory record

A memory record is a durable or retrieved memory source item. RelayMEM owns memory sources and candidates. RelayCTX may pack selected memory content, but compiled context does not become a memory record by default.

## Minimal field groups

### CompilePlan

```yaml
plan_id: compile_plan_001
route: relaylm-default
mode: memory_light
backend: local
character_id: default
scene_id: null
room_id: null
planned_block_ids:
  - common_runtime_policy
  - character_soul_anchor
  - character_output_policy
  - scene_state
token_budget_status: within_budget
apply_eligible: true
blocking_reasons: []
```

### CompileResult

```yaml
result_id: compile_result_001
plan_id: compile_plan_001
rendered_block_ids:
  - common_runtime_policy
  - character_soul_anchor
  - character_output_policy
  - scene_state
omitted_block_ids: []
message_count: 2
backend_compatible: true
compiled_messages_ready: true
```

### CompileDecision

```yaml
decision_id: compile_decision_001
plan_id: compile_plan_001
result_id: compile_result_001
decision_state: COMPILE_APPLY
apply_compiled_messages: true
diagnostics_only: false
fallback_reason: null
blocking_reasons: []
```

### Diagnostics

```yaml
selected_route: relaylm-default
selected_mode: memory_light
character_id: default
scene_id: null
room_id: null
block_ids:
  - common_runtime_policy
  - character_soul_anchor
  - character_output_policy
  - scene_state
omitted_block_ids: []
fallback_reason: null
token_budget_status: within_budget
profile_source_status: ok
scene_source_status: ok
```

### TraceEvent

```yaml
event_type: runtime_compile_decision
request_id: req_001
route: relaylm-default
mode: memory_light
decision_state: COMPILE_APPLY
apply_compiled_messages: true
block_count: 4
omitted_block_count: 0
fallback_reason: null
```

## Lifecycle

Normal apply lifecycle:

```text
CompilePlan
  -> CompileResult
  -> CompileDecision
  -> outbound payload selection
  -> Diagnostics / TraceEvent
```

Dry-run lifecycle:

```text
CompilePlan
  -> CompileDecision(COMPILE_DRY_RUN)
  -> Diagnostics / TraceEvent
  -> pass-through forwarding
```
Diagnostics-only dry-run paths should still emit `CompileDecision` with `decision_state = COMPILE_DRY_RUN` and `diagnostics_only = true` so decision logs and traces remain consistent with gate semantics.

Shadow-only lifecycle:

```text
CompilePlan
  -> CompileResult
  -> CompileDecision(COMPILE_SHADOW_ONLY)
  -> pass-through or safer forwarding
  -> Diagnostics / TraceEvent
```

## State and content rules

- Compile objects are request-local unless a future trace or audit layer persists them.
- Trace events should avoid full prompt text by default.
- RelaySOUL content-free artifacts must not embed runtime compiled prompt text.
- Failed plans, results, or decisions should prefer pass-through or safe fallback over hard rejection.
- IDs should be stable enough for logs and tests, but not durable storage IDs unless a future persistence layer defines them.

## Relationships

### Runtime Compile Gate

The Runtime Compile Gate consumes a plan/result and emits a decision.

```text
CompilePlan + optional CompileResult + preflight status
  -> Runtime Compile Gate
  -> CompileDecision
```

### Safe SOUL / Scene / CTX Compile Chain

The safe chain defines the process. This contract defines the object vocabulary.

```text
safe chain = process
artifact contract = object vocabulary
compile gate = runtime apply decision
```

### RelaySOUL

RelaySOUL owns persona-source mutation workflows. Runtime compile artifacts describe request forwarding decisions and should remain separate.

## Minimal MVP target

A minimal runtime artifact contract should support:

1. `CompilePlan` with planned block IDs and fallback reasons
2. `CompileResult` with rendered/omitted block IDs and message count
3. `CompileDecision` with decision state and apply flag
4. diagnostics that explain mode, route, scene, block order, and fallback reasons
5. trace events that avoid full prompt text by default

## Future extensions

Future work can add:

- schema version fields
- request lineage IDs
- stable prefix hashes
- token estimates per block
- shadow compare summaries
- risk scores
- RelayTRC export format
- operator-visible diagnostics endpoint
