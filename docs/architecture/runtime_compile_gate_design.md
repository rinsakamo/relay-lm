---
relaylm_doc_type: subsystem_architecture
relaylm_authority: transitional_runtime_compile_gate_current_implementation_note
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: runtime
relaylm_update_trigger:
  - current compile apply wiring or diagnostics schema changes
  - the legacy consumer migration and removal gate closes
relaylm_not_authoritative_for:
  - canonical compile/checkpoint architecture
  - exact compile artifact fields or target decision taxonomy
  - repository-wide implementation completion
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - runtime/compile-and-checkpoint.md
relaylm_related_contracts:
  - ../contracts/runtime_compile_artifact_contract.md
  - ../contracts/runtime_compile_current_target.md
  - managed_route_fallback_contract.md
---
# Transitional Runtime Compile Gate Implementation Note

## Status

This path is a closed transitional current-implementation note retained for existing documentation consumers. Canonical subsystem architecture is [Runtime Compile and Checkpoint Architecture](runtime/compile-and-checkpoint.md). Exact artifact vocabulary and current/target interpretation are owned by the [Runtime Compile Artifact Contract](../contracts/runtime_compile_artifact_contract.md) and [Runtime Compile Current / Target Boundary](../contracts/runtime_compile_current_target.md).

This page does not own target architecture or exact schemas and must not gain new consumers. Its removal gate is registered in `records/documentation/transitional-assets.json`.

## Current implementation boundary

Current request compilation has two distinct implemented surfaces:

- `relaylm.compile_gate.CompileApplyDecision` decides whether the current profile-compiler result is applied;
- `relaylm.diagnostics.build_compile_decision_dry_run` emits the content-free `mvp-ctx-apply-0` diagnostics artifact used by the request path.

The current diagnostics artifact mirrors the current profile-compiler decision. It does not implement the complete target plan/result/decision family, route-authority typing, forwarded-payload-source typing, authority-safe managed fallback construction, or the complete `BLOCKED` taxonomy.

The narrow client-history exclusion apply path is a separate current backend-forward boundary. Consumers must inspect the implemented schema/version and actual forwarded payload source rather than infer current behavior from a target state name.

## Authority rule

- Explicit `pass_through` routes may delegate context authority to the client.
- RelayLM-managed routes remain RelayLM-owned during dry run, shadow, fallback, and failure.
- Managed failure must not restore excluded prior history or raw client system/developer messages.

The exact rule is owned by the compile contracts and the [Managed-Route Fallback Authority Contract](managed_route_fallback_contract.md).

## Current non-goals

This current implementation note does not claim that RelayLM already provides:

- the complete target compile taxonomy;
- a fully typed SCN/INT/MEM/CTX compile input chain;
- general authority-safe minimal fallback construction;
- complete blocked-state handling;
- checkpoint, resume, or recovery apply.

## Removal gate

Delete this path after every current consumer links directly to `runtime/compile-and-checkpoint.md` and the owning compile contracts, link and authority validation are green, and the retirement manifest records the old path. Historical wording remains recoverable through Git.
