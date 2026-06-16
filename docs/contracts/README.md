# RelayLM Contract Docs

This directory collects RelayLM contract, artifact, schema, approval, and gate documentation.

The contract files tracked by this index are housed in this directory. Related architecture documents remain under `docs/architecture/` and are linked where they define the runtime policy consumed by a contract.

Before treating a proposed schema as the current wire contract, use the [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md). A current contract should identify its implemented producer, consumer, schema/version, and dry-run/apply posture; otherwise a `v1` example is a target design.

## Runtime and compiler contracts

- [Runtime compile current / target boundary](runtime_compile_current_target.md)
- [Runtime compile artifact contract](runtime_compile_artifact_contract.md)
  - related design: [Runtime Compile Gate Design](../architecture/runtime_compile_gate_design.md)
- [Context compiler contract](context_compiler_contract.md)
- [RelayRUN recovery response generator current / target boundary](relayrun_recovery_response_generator_current_target.md)
- [RelayRUN recovery response generator contract](relayrun_recovery_response_generator_contract.md)
  - related design: [RelayRUN Runtime Checkpoint Design](../architecture/relayrun_runtime_checkpoint_design.md)

The current compile decision is the small `CompileApplyDecision` contract; proposed v1 plan/result/decision projections are target forms. The diagnostics-only recovery-response artifact is implemented, but generator execution and visible recovery output are not.

## RelaySOUL contracts

- [RelaySOUL patch candidate contract](relaysoul_patch_candidate_contract.md)
- [RelaySOUL patch schema](relaysoul_patch_schema.md)
- [RelaySOUL revision contract](relaysoul_revision_contract.md)
- [RelaySOUL approval contract](relaysoul_approval_contract.md)
- [RelaySOUL persistence contract](relaysoul_persistence_contract.md)
- [RelaySOUL patch compile dry-run contract](relaysoul_compile_dry_run_contract.md)
- [RelaySOUL explicit approval artifact contract](relaysoul_explicit_approval_artifact_contract.md)
- [RelaySOUL preflight lineage freshness policy](relaysoul_preflight_lineage_freshness_policy.md)

The `mvp-soul-0` five-file allowlist is current compatibility behavior, not the target three-file RelaySOUL ownership boundary. Actual apply, rollback, and persistence execution remain disabled.

## Placement rule

Create new contract, artifact, schema, approval, and gate docs directly under `docs/contracts/`. Keep MVP summaries under `docs/mvp/`, architecture documents under `docs/architecture/`, and smoke/manual runbooks under `docs/smoke/`.
