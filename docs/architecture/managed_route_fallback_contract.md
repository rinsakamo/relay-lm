# Managed-Route Fallback Authority Contract

## Status

This document clarifies the stable fallback boundary. Current implementation status remains in `PROJECT_STATUS.md` and `pipeline_implementation_plan.md`.

## Explicit pass-through route

An explicit `pass_through` route delegates context authority to the client. Compatible messages may be forwarded because route configuration selected that behavior.

## Managed route

A managed route uses this order:

```text
full RelayLM-managed payload
  -> reduced RelayLM-managed payload
  -> minimal RelayLM-managed payload
  -> fail closed
```

A managed failure does not change route authority. Excluded prior history is not restored as fallback.

## Current boundary

The current compiler does not yet emit the complete target fallback and blocked-state schema. Consumers must inspect the actual forwarded payload, route mode, current compile-decision fields, and payload-replacement reasons.

## Required migration

A future implementation must update route-authority typing, managed history exclusion, minimal fallback construction, compile-gate projections, PipelineContext source tracking, RelayRUN routing, compatibility checks, and smoke coverage together.

## References

- [Runtime Compile Gate Design](runtime_compile_gate_design.md)
- [Client History Authority Contract](client_history_authority_contract.md)
- [Client Instruction Authority Contract](client_instruction_authority_contract.md)
- [Current / Target / Migration Guide](current_target_migration_guide.md)
