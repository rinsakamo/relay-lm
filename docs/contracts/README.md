---
relaylm_doc_type: documentation_index
relaylm_authority: contract_documentation_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: contracts
relaylm_update_trigger:
  - contract entry points change
  - current contract implementation posture changes
  - schema ownership changes
relaylm_not_authoritative_for:
  - repository-wide current runtime behavior
  - MVP dependency sequencing
  - historical implementation evidence
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM Contract Docs

This directory collects RelayLM contract, artifact, schema, approval, and gate documentation.

The contract files tracked by this index are housed in this directory. Related architecture documents remain under `docs/architecture/` and are linked where they define the runtime policy consumed by a contract.

Before treating a proposed schema as the current wire contract, use the [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md). A current contract should identify its implemented producer, consumer, schema/version, and dry-run/apply posture; otherwise a `v1` example is a target design.

## Runtime and compiler contracts

- [Runtime compile current / target boundary](runtime_compile_current_target.md)
- [Runtime compile artifact contract](runtime_compile_artifact_contract.md)
  - related design: [Runtime Compile Gate Design](../architecture/runtime_compile_gate_design.md)
- [Context compiler contract](context_compiler_contract.md)
- [RelayCTX short-term runtime contract](relayctx_short_term_runtime_contract.md)
  - current four-stage default-off diagnostics/injection chain: extraction dry-run -> block assembly dry-run -> injection preflight -> gated apply
  - current full blocked-reason taxonomy and stage ordering for the apply gate in `relaylm/relayctx_repack.py`
- [Client instruction artifact current / target contract](client_instruction_target_artifact_contract.md)
  - current strict read-only `relaylm.client_instruction_cache.v0` lookup validation
  - current trusted runtime-private typed-parse validation and default-off, dry-run-first cache-writer planning/apply
  - target backend-response control-envelope producer, semantic RelaySCN projection apply, retry, and parser-versioned compatibility
  - related authority: [Client Instruction Authority Contract](../architecture/client_instruction_authority_contract.md)
- [RelayRUN recovery response generator current / target boundary](relayrun_recovery_response_generator_current_target.md)
- [RelayRUN recovery response generator contract](relayrun_recovery_response_generator_contract.md)
  - related design: [RelayRUN Runtime Checkpoint Design](../architecture/relayrun_runtime_checkpoint_design.md)
- [LAT-1 RelayRUN `timing_summary` artifact schema](../architecture/lat1_latency_measurement.md)
  - `relayrun.timing_summary.v0`: numeric-only per-request RelayRUN node timing rollup, measurement only

Current compile behavior has two implemented surfaces:

1. `relaylm.compile_gate.CompileApplyDecision`, which decides whether the current profile-compiler result is applied.
2. The content-free `mvp-ctx-apply-0` artifact built by `relaylm.diagnostics.build_compile_decision_dry_run`, which records the current request-path `COMPILE_APPLY` or `COMPILE_DRY_RUN` diagnostics state.

Proposed runtime-compile v1 plan/result/decision projections, route-authority typing, forwarded-payload-source typing, managed fallback, and complete `BLOCKED` behavior remain target forms. Client-instruction lookup validation, content-free cache-hit projection diagnostics, trusted runtime-private typed-parse validation, and the default-off/dry-run-first C5b/C5c cache-writer path are implemented. Backend-response parsing, arbitrary frontend-metadata trust, semantic RelaySCN projection apply, and parser-versioned lookup/write compatibility are not implemented. The diagnostics-only recovery-response artifact is implemented, but generator execution and visible recovery output are not.

## RelaySOUL contracts

- [RelaySOUL patch candidate contract](relaysoul_patch_candidate_contract.md)
- [RelaySOUL patch schema](relaysoul_patch_schema.md)
- [RelaySOUL revision contract](relaysoul_revision_contract.md)
- [RelaySOUL approval contract](relaysoul_approval_contract.md)
- [RelaySOUL persistence contract](relaysoul_persistence_contract.md)
- [RelaySOUL patch compile dry-run contract](relaysoul_compile_dry_run_contract.md)
- [RelaySOUL explicit approval artifact contract](relaysoul_explicit_approval_artifact_contract.md)
- [RelaySOUL preflight lineage freshness policy](relaysoul_preflight_lineage_freshness_policy.md)

The `mvp-soul-0` five-file allowlist is current compatibility behavior, not the target file-first RelaySOUL ownership boundary. Actual apply, rollback, and persistence execution remain disabled.

## Placement rule

Create new contract, artifact, schema, approval, and gate docs directly under `docs/contracts/`. Keep MVP summaries under `docs/mvp/`, architecture documents under `docs/architecture/`, and smoke/manual runbooks under `docs/smoke/`.
