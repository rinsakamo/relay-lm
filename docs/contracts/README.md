# RelayLM Contract Docs

This directory collects RelayLM contract, artifact, schema, approval, and gate documentation.

The contract files tracked by this index are housed in this directory. Related architecture documents remain under `docs/architecture/` and are linked where they define the runtime policy consumed by a contract.

## Runtime and compiler contracts

- [Runtime compile artifact contract](runtime_compile_artifact_contract.md)
  - related design: [Runtime Compile Gate Design](../architecture/runtime_compile_gate_design.md)
- [Context compiler contract](context_compiler_contract.md)
- [RelayRUN recovery response generator contract](relayrun_recovery_response_generator_contract.md)
  - related design: [RelayRUN Runtime Checkpoint Design](../architecture/relayrun_runtime_checkpoint_design.md)

## RelaySOUL contracts

- [RelaySOUL patch candidate contract](relaysoul_patch_candidate_contract.md)
- [RelaySOUL patch schema](relaysoul_patch_schema.md)
- [RelaySOUL revision contract](relaysoul_revision_contract.md)
- [RelaySOUL approval contract](relaysoul_approval_contract.md)
- [RelaySOUL persistence contract](relaysoul_persistence_contract.md)
- [RelaySOUL patch compile dry-run contract](relaysoul_compile_dry_run_contract.md)
- [RelaySOUL explicit approval artifact contract](relaysoul_explicit_approval_artifact_contract.md)
- [RelaySOUL preflight lineage freshness policy](relaysoul_preflight_lineage_freshness_policy.md)

## Placement rule

Create new contract, artifact, schema, approval, and gate docs directly under `docs/contracts/`. Keep MVP summaries under `docs/mvp/`, architecture documents under `docs/architecture/`, and smoke/manual runbooks under `docs/smoke/`.
