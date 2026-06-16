# Runtime Compile Current / Target Boundary

## Current implemented surfaces

Current request compilation has two distinct implemented contract surfaces.

### 1. Typed compile apply decision

Current request compilation uses:

```text
relaylm.request_compiler.compile_chat_payload_if_enabled
relaylm.compile_gate.decide_compile_apply
relaylm.compile_gate.CompileApplyDecision
```

Current `CompileApplyDecision` fields are:

```text
should_apply
mode_applied
profile_compile_ready
reason
```

This object decides whether the current profile-compiler result is applied. It is not the complete target Runtime Compile Gate schema.

### 2. Current compile-decision diagnostics artifact

The current request path also builds a separate content-free diagnostics artifact:

```text
producer:
  relaylm.diagnostics.build_compile_decision_dry_run

schema_version:
  mvp-ctx-apply-0

request-path consumer/storage:
  RequestDiagnostics.compile_decision_dry_run
  trace/diagnostics projection
```

Current fields include:

```text
decision_id
plan_id
result_id
decision_state
apply_compiled_messages
diagnostics_only
fallback_reason
blocking_reasons
selected_route
selected_mode
backend
character_id
compiled_message_count
omitted_block_ids
token_budget_status
```

The current request path emits `COMPILE_APPLY` when `CompileApplyDecision.should_apply=true`; otherwise it emits `COMPILE_DRY_RUN`. This diagnostics artifact mirrors the current profile-compiler decision but does not add route-authority typing, forwarded-payload-source typing, a managed fallback builder, or a complete blocked-state taxonomy.

## Current compiler ordering

The current profile compiler runs before normalized target SCN, typed INT, and target Retrieval handoffs are available. It accepts incoming messages and configured profile/seed-memory sources.

The narrow `client_history_exclusion_apply.v0` boundary may subsequently replace the current `memory_light` payload for supported no-instruction managed requests. That backend-forward gate is a separate current boundary rather than a complete Runtime Compile Gate implementation.

## Target architecture

The target managed compiler consumes canonicalized current evidence, approved durable sources, normalized SCN, typed INT decisions, selected MEM evidence, and CTX working-state selection.

The target artifact family adds explicit versioned plan/result/decision/trace projections with, at minimum:

- route-authority class,
- forwarded-payload-source class,
- managed fallback class,
- compatibility result,
- complete decision taxonomy,
- explicit `BLOCKED` behavior.

Proposed schemas such as `relaylm.compile_plan_projection.v1`, `relaylm.compile_result_projection.v1`, and `relaylm.compile_decision_projection.v1` are target forms, not current wire schemas.

Conceptual target states that are not all current implementations include:

```text
PASS_THROUGH
COMPILE_DRY_RUN
COMPILE_SHADOW_ONLY
COMPILE_APPLY
COMPILE_FALLBACK
BLOCKED
```

Current `mvp-ctx-apply-0` use of `COMPILE_APPLY` and `COMPILE_DRY_RUN` must not be mistaken for implementation of the complete target taxonomy.

## Authority rule

- Explicit `pass_through` delegates client context authority.
- A managed route remains RelayLM-owned during dry run, shadow, fallback, or failure.
- Managed failure does not restore excluded prior history or raw client system/developer messages.

See [Managed-Route Fallback Authority Contract](../architecture/managed_route_fallback_contract.md).

## Required migration

A future implementation must update together:

1. compiler ordering and canonicalization apply,
2. SCN/INT/MEM/CTX typed handoffs,
3. route-authority typing,
4. forwarded-payload-source tracking,
5. authority-safe minimal managed fallback construction,
6. versioned plan/result/decision projections,
7. `COMPILE_FALLBACK` and `BLOCKED` behavior,
8. PipelineContext mutation/source tracking,
9. RelayRUN projections and lineage,
10. authority, content-free, and integration smoke coverage.

## Consumer rule

Consumers must distinguish:

- `CompileApplyDecision`,
- the current `mvp-ctx-apply-0` diagnostics artifact,
- proposed v1 target projections.

They must inspect the implemented schema/version and actual forwarded-payload source. They must not infer current authority or fallback behavior from a target decision-state name alone.

## References

- [Context Compiler Contract](context_compiler_contract.md)
- [Runtime Compile Artifact Contract](runtime_compile_artifact_contract.md)
- [Runtime Compile Gate Design](../architecture/runtime_compile_gate_design.md)
- [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md)
