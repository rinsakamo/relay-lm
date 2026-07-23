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
- [RelayINT quick-clarification runtime contract](relayint_quick_clarification_runtime_contract.md)
  - current three-stage default-off plan-only chain: fast-path dry-run -> quick-clarification preflight -> apply plan
  - current candidate-action/clarification-type/blocked-reason taxonomies in `relaylm/relayint.py`; actual user-visible apply remains target-only
- [PipelineNodeResult contract](pipeline_node_result_contract.md)
  - current shared, cross-cutting `PipelineNodeResult` shape, immutability/detachment semantics, and request-local collection in `relaylm/pipeline_node_result.py` and `relaylm/pipeline_context.py`
  - current 16-node emitter list and non-authority over routing/RelayRUN
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

## Documentation governance contract

- [Documentation Governance Contract](documentation-governance.md) owns the canonical active-document graph, stable granularity, retained-record allowlist, retirement manifest, Git recoverability, generic validation families, and the no-growth/removal gates for legacy source-specific cutover machinery.
- Machine-readable schemas live under [`schemas/documentation-governance-v1/`](schemas/documentation-governance-v1/).
- Current documentation governance records live under [`records/documentation/`](../../records/documentation/); they are provenance and validation inputs, not semantic authority.

## Governed evidence contracts

- [Governed Evidence Contract Family](governed-evidence-contract-family.md) defines shared identity, authority primitives, terminology, and cross-contract invariants.
- [Governed Source Capture and Admission](governed-source-capture-admission.md) owns source capture, immutable `SourceEvent`, admission, quarantine review, replay resolution, and validation-bundle binding.
- [Evidence Governance and Access](evidence-governance-access.md) owns retention, grants and authorizations, review access, restriction, redaction, purge, export eligibility, and replication eligibility.
- [Source Metadata, Lineage, and Derived Artifacts](source-metadata-lineage-derived-artifacts.md) owns effective metadata revisions, lineage, and derived-artifact lifecycle.
- [Evidence Streams, Coverage, and Authority-Change Feed](evidence-streams-change-feed.md) owns capture sequencing, terminal coverage, privacy partitions, and authority-change projections.
- [Assistant-Response Evidence Binding](assistant-response-evidence-binding.md) owns pre-emission reservation, canonical output binding, response finalization, delivery observations, and recovery.

These six documents are exact normative **target** contracts. They do not claim that the corresponding runtime, storage, migration, or deployment behavior is implemented.

Machine-readable Contract 1 v7 materials:

- [schema catalog](schemas/contract1-v7/schema-catalog.json) and [Draft 2020-12 bundle](schemas/contract1-v7/relaylm-contract1-v7.bundle.schema.json);
- [valid fixtures](fixtures/contract1-v7/valid/) and [invalid fixtures](fixtures/contract1-v7/invalid/);
- [schema and lifecycle validator](../../scripts/relaylm_contract1_v7_validate.py);
- [prose/schema equivalence validator](../../scripts/relaylm_contract1_v7_equivalence.py).

## RelayCTX Session Evidence Overlay contract

- [RelayCTX Session Evidence Overlay (CTX-OVL) contract](relayctx-session-evidence-overlay.md)
  - target contract only; owns CTX-OVL admission/update/removal, bounded catch-up from governed evidence on a later admitted request, shared-scene/participant/relationship/quarantine partitioning, scene/partition epoch fencing, unknown-participant non-shadowing, rebuildability/restart behavior, the context-compiler read interface, and the bounded content-free Reflex Snapshot RelayATN may read
  - consumes, but does not own or advance, Contract 1D source/change coverage and Contract 1B authorization watermarks
  - does not define Shared Assessment, Subjective MEM, storage authority, RelaySLP, or RelayATN's own architecture

Machine-readable CTX-OVL v1 materials:

- [compact single-file Draft 2020-12 schema bundle](schemas/ctx-ovl-v1/relaylm-ctx-ovl-v1.schema.json) and [direct-reference catalog](schemas/ctx-ovl-v1/schema-catalog.json);
- [valid fixtures](fixtures/ctx-ovl-v1/valid/) and [invalid fixtures](fixtures/ctx-ovl-v1/invalid/);
- [schema and cross-record invariant validator](../../scripts/relaylm_ctx_ovl_v1_validate.py);
- [prose/schema equivalence and coverage validator](../../scripts/relaylm_ctx_ovl_v1_equivalence.py);
- [invalid-fixture registry guard](../../scripts/relaylm_ctx_ovl_v1_fixture_registry_guard.py).

## Shared Assessment and Subjective MEM contract

- [Shared Assessment and Subjective MEM contract](shared-assessment-subjective-mem.md)
  - target logical contract only; owns character-independent Shared Assessment revision/current-state authority and character-scoped Subjective MEM decision, revision, relation, lifecycle, scope, and ordinary-Retrieval eligibility boundaries
  - fixes grounded-content / subjective-meaning separation, SOUL-centered and SCN/REL-bounded formation, EMO non-authority, false-merge-safe decisions, and Primary/Secondary versus Semantic/Episodic orthogonality
  - consumes governed Evidence and CTX-OVL boundaries but does not define physical storage, runtime implementation, retrieval ranking, migration, or deployment

Machine-readable Subjective MEM v1 materials:

- [compact single-file Draft 2020-12 schema bundle](schemas/subjective-mem-v1/relaylm-subjective-mem-v1.schema.json) and [direct-reference catalog](schemas/subjective-mem-v1/schema-catalog.json);
- [valid fixtures](fixtures/subjective-mem-v1/valid/) and [invalid fixtures](fixtures/subjective-mem-v1/invalid/);
- [schema and cross-record invariant validator](../../scripts/relaylm_subjective_mem_v1_validate.py);
- [prose/schema/catalog/fixture equivalence validator](../../scripts/relaylm_subjective_mem_v1_equivalence.py);
- [invalid-fixture registry guard](../../scripts/relaylm_subjective_mem_v1_fixture_registry_guard.py).

## Subjective MEM storage authority contract

- [Subjective MEM Storage Authority and Commit Protocol Contract](subjective-mem-storage-authority-and-commit-protocol.md)
  - target logical contract only; owns canonical Markdown, rebuildable projection, durable operations, receipt finalization, digest/revision recovery, lifecycle-tombstone agreement, durable usage events, backup-set, and hard-cutover boundaries
  - fixes that Markdown owns committed memory semantics and lifecycle-visible state while a matching operations receipt finalizes publication without becoming a second content authority
  - treats PR #578 as feasibility evidence only and does not select final syntax, SQLite schema, filesystem implementation, migration procedure, or supported platform

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

Create new exact contract, artifact, schema, approval, and gate documents under `docs/contracts/`. Keep architecture under `docs/architecture/`, procedures under `docs/operations/` or `docs/guides/`, and narrowly continuing machine-readable records under `records/`. Transitional evidence and smoke collections do not define permanent placement; their owning D2-D6 batch synthesizes, reclassifies, or retires them without redirects.
