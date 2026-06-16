# Runtime Compile Artifact Contract

## Scope

This contract separates current compile artifacts from the target plan/result/decision family.

See [Context Compiler Contract](context_compiler_contract.md), [Runtime Compile Gate Design](../architecture/runtime_compile_gate_design.md), and [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md).

## Current implemented contract

Current compiler:

```text
relaylm.request_compiler.compile_chat_payload_if_enabled
relaylm.request_compiler.CompiledRequest
```

Current gate result:

```text
relaylm.compile_gate.CompileApplyDecision
```

Current decision fields:

```text
should_apply
mode_applied
profile_compile_ready
reason
```

Current compile logs expose bounded profile, memory-selection, stable-prefix, context-block, and budget diagnostics. Current code does not emit the complete target v1 plan/result/decision projection family.

## Current no-instruction apply artifact

```text
schema: client_history_exclusion_apply.v0
producer: relaylm.client_history_exclusion_apply.build_client_history_exclusion_apply
runtime: relaylm.client_history_exclusion_apply_runtime.run_client_history_exclusion_apply_runtime
```

The request-local result may carry a content-bearing rebuilt payload. Its diagnostic and node projections copy only typed metadata.

This is a narrow managed apply artifact, not the complete target Runtime Compile Gate.

## Target object boundary

```text
CompilePlan
CompileResult
CompileDecision
Diagnostics
TraceEvent
RelaySOUL artifact
Memory record
```

These objects have different ownership.

### Target CompilePlan

Describes intended blocks, authority class, mode, budget, readiness, fallback availability, and reason IDs. It does not prove that messages were forwarded.

### Target CompileResult

Contains the request-local rendered backend candidate and may be content-bearing. It does not enter generic trace storage directly.

### Target CompileDecision

Selects explicit pass-through, dry-run, shadow, apply, managed fallback, or blocked behavior after route authority is known.

### Target TraceEvent

Contains only typed content-free decision metadata for RelayRUN linkage and observability.

## Authority rules

- pass-through requires explicit delegated route authority,
- managed dry-run/shadow/fallback preserves RelayLM-owned authority,
- managed failure does not restore prior client history,
- a request-local compile result is not RelaySOUL approval or a memory record.

## Target schema names

Proposed target schemas may include:

```text
relaylm.compile_plan_projection.v1
relaylm.compile_result_projection.v1
relaylm.compile_decision_projection.v1
relaylm.runtime_compile_event.v1
```

They are not current wire contracts until implemented producers and consumers exist.

## Content rules

Runtime-private compile objects may contain backend messages, block content, selected evidence, compatibility details, and fallback payloads.

Default projections must not contain raw messages, prompt blocks, memory/persona bodies, final response text, secret-bearing paths/URLs, or arbitrary nested runtime artifacts.

## Required migration

Update together:

1. plan/result/decision schemas,
2. route-authority typing,
3. instruction-bearing managed apply,
4. forwarded-payload source tracking,
5. reduced/minimal managed payload construction,
6. PipelineContext mutation reasons,
7. RelayRUN lineage/checkpoint projections,
8. compiler and authority smoke tests.

## Consumer rule

Consumers follow the implemented schema/version and actual forwarded-payload source. They must not infer current behavior from a target decision-state name alone.
