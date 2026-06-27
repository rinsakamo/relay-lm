---
relaylm_doc_type: documentation_index
relaylm_authority: repository_documentation_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - documentation entry points change
  - canonical authority ordering changes
  - placement rules change
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact schema details
  - implementation phase completion claims
relaylm_current_status_source: PROJECT_STATUS.md
---
# RelayLM Documentation

RelayLM documentation is AI-first. Documents must remain correct when retrieved partially; current documents must not rely on a later "supersedes earlier text" correction inside the same file.

## Start here

- [Current project status](PROJECT_STATUS.md) — the single current implementation status authority.
- [Project execution plan](architecture/project_execution_plan.md) — the single MVP execution plan and post-MVP roadmap authority.
- [Documentation model](DOCUMENTATION_MODEL.md) — document types, metadata, authority, AI reading rules, and the parallel implementation/convergence flow.
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md) — component responsibility and canonical target order.
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) — compatibility interpretation.
- [E1 MVP evaluation consolidation](architecture/e1_evaluation_consolidation.md) — current E1 evidence inventory and direct Home-origin formation decision.
- [E1 local runtime evaluation](architecture/e1_local_runtime_evaluation_2026_06_25.md) — workstation evidence and known product gaps.
- [MVP evidence index](mvp/README.md) — historical snapshots and per-PR implementation completion reports.

## Product-critical boundaries

- [Phase 6 I1-B runtime enqueue and protected source capture](architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md)
- [Phase 6-C1 Primary MEM worker contract](architecture/phase6c1_primary_mem_worker_contract.md)
- [Phase 6-C1-2 one-claimed worker](architecture/phase6c1_one_claimed_primary_worker_handoff.md)
- [Phase 6-C1-5 durable protected source persistence](architecture/phase6c1_durable_protected_source_persistence.md)
- [Phase 6-C2 one queued-job integration](architecture/phase6c2_one_queued_primary_worker_integration.md)
- [O0 local one-job runner](architecture/o0_local_one_job_runner.md)
- [O1A two-lane scheduler contract](architecture/o1a_two_lane_scheduler_contract.md)
- [O1B sealed I1-G replay lane](architecture/o1b_sealed_i1g_replay_lane.md)
- [O1C eligible B2/B3 queue lane](architecture/o1c_eligible_b2_queue_lane.md)
- [O1D1 accepted scheduler gates and one production round](architecture/o1d1_production_scheduler_round.md)
- [O1D2 deterministic scheduler policy](architecture/o1d2_scheduler_policy.md)
- [O1E scheduler operational controls](architecture/o1e_scheduler_operational_controls.md)
- [O1F operational validation](architecture/o1f_operational_validation.md)
- [O1 manual one-round runbook](smoke/o1_manual_one_round_runbook.md)
- [I1-G durable-finalization contract and completed GA-GE boundaries](architecture/i1g_pre_enqueue_durable_finalization_contract.md)
- [I1-GD durable-finalization retention and isolation lifecycle](architecture/i1gd_durable_finalization_retention_cleanup.md)
- [I1-GE Durable-finalization Crash Validation](architecture/i1ge_durable_finalization_crash_validation.md)
- [Integration I1 Primary MEM two-turn recall](architecture/integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-2 real SOUL Lab observation](architecture/phase_i2_real_soul_lab_observation.md)
- [Phase I-3 auditable Primary MEM Correct](architecture/phase_i3_auditable_primary_mem_correct.md)
- [Phase I-4A Primary MEM Forget / Hide contract](architecture/phase_i4_primary_mem_forget_hide_contract.md)
- [Phase I-4B Primary Current State and Shared Mutation Fence](architecture/phase_i4b_primary_current_state_shared_fence.md)
- [Phase I-4C1 Primary Forget Hidden-Successor Commit](architecture/phase_i4c1_primary_forget_hidden_successor.md)
- [Phase I-4C2 Primary Forget Recovery and Finalization](architecture/phase_i4c2_primary_forget_recovery_finalization.md)
- [Phase I-4D Primary retrieval exclusion](architecture/phase_i4d_primary_retrieval_exclusion.md)
- [Phase I-4E Forget API and SOUL Lab UI](architecture/phase_i4e_forget_api_ui.md)
- [Phase I-4F Forget product validation](architecture/phase_i4f_forget_validation.md)
- [Phase I-5A Pin / Unpin contract and read-only preflight](architecture/phase_i5_pin_unpin_contract.md)
- [Phase I-7A/B Held Apply / Discard contract and read-only preflight](architecture/phase_i7ab_held_apply_discard_contract.md)
- [SOUL Lab UI-B0 real Home conversation](architecture/soul_lab_ui_b0_real_home_conversation.md)
- [SOUL Lab UI-B1A lifecycle visibility](architecture/soul_lab_ui_b1a_lifecycle_visibility.md)
- [E1 MVP evaluation consolidation](architecture/e1_evaluation_consolidation.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)
- [Architecture documentation index](architecture/README.md)

## Current status pointer

Current runtime and implementation status is intentionally not summarized here. Read [Current project status](PROJECT_STATUS.md) for the current boundary. At the time this index was reviewed, Wave 4 implementation tracks, W4-INT, Wave 5 implementation tracks, W5-INT, O1F, E1, O1E, and I-4F are merged. E1 consolidation is docs/evidence-only and does not add runtime behavior. O1F is validation-only and does not add O2/O3 supervision or always-on operation.

## Wave 6 / O1F evidence

- [O1F completion report](mvp/wave6/o1f_completion_report.md)
- [O1F operational validation](architecture/o1f_operational_validation.md)

## Wave 5 / E1 evaluation evidence

- [Wave 5 Cross-Slice Convergence Audit](architecture/wave5_cross_slice_convergence_audit.md)
- [O1E completion report](mvp/wave5/o1e_completion_report.md)
- [I-4F completion report](mvp/wave5/i4f_completion_report.md)
- [E1 completion report](mvp/wave5/e1_completion_report.md)
- [O1E scheduler operational controls](architecture/o1e_scheduler_operational_controls.md)
- [Phase I-4F Forget product validation](architecture/phase_i4f_forget_validation.md)
- [E1 MVP evaluation consolidation](architecture/e1_evaluation_consolidation.md)
- [E1 local runtime evaluation](architecture/e1_local_runtime_evaluation_2026_06_25.md)

## Wave 4 implementation evidence

- [Wave 4 Cross-Slice Convergence Audit](architecture/wave4_cross_slice_convergence_audit.md)
- [O1D2 completion report](mvp/wave4/o1d2_completion_report.md)
- [I-4E completion report](mvp/wave4/i4e_completion_report.md)
- [UI-B1A completion report](mvp/wave4/ui_b1a_completion_report.md)
- [I-5A completion report](mvp/wave4/i5a_completion_report.md)
- [I-7A/B completion report](mvp/wave4/i7ab_completion_report.md)

## Target architecture and post-MVP design

- [Character belief, relationship, and social expression dynamics](architecture/character_belief_relationship_dynamics_design.md)
- [ADR: character-conditioned belief without rewriting observation](adr/character_conditioned_belief_model.md)
- [Experimental SOUL replacement and memory bootstrap](relaysoul/experimental_soul_replacement_memory_bootstrap_design.md)

These documents are target architecture only. Experimental SOUL replacement is explicitly post-MVP and does not alter the ordinary Phase I-9 revision/rollback path.

## Canonical precedence

1. `docs/PROJECT_STATUS.md` owns current implementation status and active caveats.
2. `architecture/project_execution_plan.md` owns MVP boundary, dependency sequencing, and roadmap ordering.
3. `pipeline_responsibility_design.md` owns component responsibility and canonical target order.
4. Dedicated current contracts own exact bounded behavior.
5. `current_target_migration_guide.md` owns current/target/compatibility interpretation.
6. `docs/mvp/` and `docs/architecture/` evaluation records are historical or bounded evidence unless listed as current authorities above.

## Placement rules

- repository-wide current status -> `docs/PROJECT_STATUS.md`
- MVP execution plan and post-MVP roadmap -> `docs/architecture/project_execution_plan.md`
- active and completed bounded handoffs -> `docs/architecture/`
- schemas and contracts -> `docs/contracts/`
- RelaySOUL governance -> `docs/relaysoul/`
- smoke and troubleshooting -> `docs/smoke/`
- historical rationale -> `docs/architecture/archive/`
- MVP snapshots and implementation completion reports -> `docs/mvp/`

## Parallel implementation documentation rule

For a declared parallel wave, each implementation PR must update only its code, tests/workflows, implementation-coupled exact schema/config docs, a unique slice-owned handoff, and one unique `docs/mvp/wave*/<slice>_completion_report.md`. It must not edit the shared status, execution plan, indexes, cross-slice current-target documents, previous-wave audit, or repository-wide documentation-boundary smoke merely to mark the slice complete.

After the parallel PRs merge, the wave convergence thread updates Project Status, Project Execution Plan, both documentation indexes, relevant current/target documents, completion-report links, and repository-wide documentation smoke in one PR. The next wave and release/evaluation gate remain closed until that convergence PR is green and merged.

For a non-parallel slice without a reserved convergence thread, the implementation PR may still update all affected current documents atomically. The authoritative rules and reserved shared-file list are in [Documentation Model](DOCUMENTATION_MODEL.md).
