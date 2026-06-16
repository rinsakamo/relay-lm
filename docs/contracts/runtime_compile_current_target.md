# Runtime Compile Current / Target Boundary

## Current implemented

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

The current profile compiler runs before normalized SCN, typed INT, and target Retrieval handoffs are available. It accepts incoming messages and configured profile/seed-memory sources.

## Target architecture

The target managed compiler consumes canonicalized current evidence, approved durable sources, normalized SCN, typed INT decisions, selected MEM evidence, and CTX working-state selection.

The target compile artifact family may include versioned plan, result, decision, and trace projections with route-authority and forwarded-payload-source fields.

Those proposed v1 projections are not current wire schemas.

## Authority rule

- Explicit `pass_through` delegates client context authority.
- A managed route remains RelayLM-owned during dry run, shadow, fallback, or failure.
- Managed failure does not restore excluded prior history.

See [Managed-Route Fallback Authority Contract](../architecture/managed_route_fallback_contract.md).

## Required migration

A future implementation must update compiler ordering, canonicalization apply, SCN/INT/MEM/CTX handoffs, route-authority typing, minimal managed fallback, PipelineContext source tracking, RelayRUN projections, and smoke coverage together.

## Consumer rule

Consumers must use the implemented schema/version and inspect the actual forwarded-payload source. They must not infer current behavior from a target decision-state name alone.

## References

- [Context Compiler Contract](context_compiler_contract.md)
- [Runtime Compile Artifact Contract](runtime_compile_artifact_contract.md)
- [Runtime Compile Gate Design](../architecture/runtime_compile_gate_design.md)
- [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md)
