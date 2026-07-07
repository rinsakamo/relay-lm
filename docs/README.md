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
- [File-first Character Workspace design](architecture/file_first_character_workspace_design.md) — the current product direction reset target: editable Markdown character sources compiled into runtime projections.
- [CW-A1 File-first Source Tree and Parser Contracts](architecture/cw_a1_file_first_source_tree_parser_contracts.md) — the current read-only source tree/parser contract slice for the file-first Character Workspace reset.
- [CW-A5 Character Creation, Templates, and Showcase Import](architecture/cw_a5_character_creation_templates_showcase_import.md) — the current bounded creation/template/import slice for deterministic local Character Workspace creation.
- [O2 Supervised Scheduler Service](architecture/o2_supervised_scheduler_service.md) — the current opt-in supervised local scheduler service boundary.
- [O3 Always-On Local Scheduler](architecture/o3_always_on_local_scheduler.md) — the current opt-in local CLI/process wrapper boundary.
- [RelayREL relationship design](architecture/relayrel_relationship_design.md) — target-specific relationship state, relationship-conditioned interaction policy, and `RELATIONSHIP.md` / `relationships/<target>.md` ownership.
- [Character template creation flow](architecture/character_template_creation_flow.md) — no-character startup, Quick/Advanced Create, template import, and showcase policy.
- [Documentation model](DOCUMENTATION_MODEL.md) — document types, metadata, authority, AI reading rules, and the parallel implementation/convergence flow.
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md) — component responsibility and canonical target order.
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) — compatibility interpretation.
- [E1 MVP evaluation consolidation](architecture/e1_evaluation_consolidation.md) — current E1 evidence inventory and completed E1-R1 through E1-R5 quality work.
- [MVP evidence index](mvp/README.md) — historical snapshots and per-PR implementation completion reports.

The current product target is no longer only a memory-governance proxy. The MVP direction is a Markdown/file-first Character Workspace plus governed runtime behavior for relationship-, scene-, emotion-, memory-, and context-aware conversation.

## Parallel implementation documentation rule

Implementation PRs add or update their own slice handoff and `docs/mvp/wave*/<slice>_completion_report.md` only. Shared current-status and execution-plan documents may receive the minimum anchors needed to keep active validation green, but the wave convergence PR remains responsible for repository-wide synthesis. The next wave and release/evaluation gate remain closed until the convergence PR links the merged reports and updates shared current-status documents.

## Product-critical boundaries

- [File-first Character Workspace design](architecture/file_first_character_workspace_design.md)
- [CW-A1 File-first Source Tree and Parser Contracts](architecture/cw_a1_file_first_source_tree_parser_contracts.md)
- [CW-A5 Character Creation, Templates, and Showcase Import](architecture/cw_a5_character_creation_templates_showcase_import.md)
- [RelayREL relationship design](architecture/relayrel_relationship_design.md)
- [Character template creation flow](architecture/character_template_creation_flow.md)
- [P0 RelayREL / RelaySCN / RelayEMO ordering fix](architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md)
- [ACG-1 Analyzer Candidate Governance contract](architecture/acg1_analyzer_candidate_governance_contract.md)
- [ACG-2 Grounded Recall Detail Safety](architecture/acg2_grounded_recall_detail_safety.md)
- [ACG-3 Retrieval Query Normalization](architecture/acg3_retrieval_query_normalization.md)
- [ACG-4 Reference Intent Analyzer](architecture/acg4_reference_intent_analyzer.md)
- [ACG-5 RelayEMO Scene Cleanup](architecture/acg5_relayemo_scene_cleanup.md)
- [ACG-6 Scene-Wiki Classifier Boundary](architecture/acg6_scene_wiki_classifier.md)
- [Analyzer Candidate Governance roadmap](architecture/analyzer_candidate_governance.md)
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
- [O2 supervised scheduler service](architecture/o2_supervised_scheduler_service.md)
- [O3 always-on local scheduler](architecture/o3_always_on_local_scheduler.md)
- [O1 manual one-round runbook](smoke/o1_manual_one_round_runbook.md)
- [PM-D5 RelayMEM flat-store compatibility removal](architecture/pm_d5_relaymem_flat_store_compatibility_removal.md)
- [PM-D6 RelayINT native artifact / RelayREF wrapper removal](architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md)
- [PM-D7 runtime install hook fold-in](architecture/pm_d7_runtime_install_hook_fold_in.md)
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
- [Phase I-5B Pin / Unpin apply and ranking behavior](architecture/phase_i5b_pin_unpin_apply.md)
- [Phase I-7A/B Held Apply / Discard contract and read-only preflight](architecture/phase_i7ab_held_apply_discard_contract.md)
- [Phase I-7C Held Apply / Discard runtime governance](architecture/phase_i7c_held_apply_discard_runtime.md)
- [SOUL Lab UI-B0 real Home conversation](architecture/soul_lab_ui_b0_real_home_conversation.md)
- [SOUL Lab UI-B1A lifecycle visibility](architecture/soul_lab_ui_b1a_lifecycle_visibility.md)
- [E1 MVP evaluation consolidation](architecture/e1_evaluation_consolidation.md)
- [E1-R1 trusted Home scene admission](architecture/e1r1_trusted_home_scene_admission.md)
- [E1-R2 character-store bootstrap command](architecture/e1r2_character_store_bootstrap.md)
- [E1-R3 provenance-preserving formation summary](architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md)
- [E1-R4 retrieval-response grounding](architecture/e1r4_retrieval_response_grounding.md)
- [E1-R5 Primary MEM recall candidate discovery bridge](architecture/e1r5_primary_mem_recall_candidate_bridge.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)
- [Architecture documentation index](architecture/README.md)

## Current status pointer

Current runtime and implementation status is intentionally not summarized here. Read [Current project status](PROJECT_STATUS.md) for the current boundary. At the time this index was reviewed, Wave 3 through Wave 7 implementation tracks and W3-INT through W7-INT are merged, E1-R5 is converged as a post-Wave-7 correction, P0-PIPE is complete in PR #458, ACG-1 through ACG-6 analyzer governance slices are complete, CW-A1 through CW-A5 Character Workspace reset slices are complete, O2/O3 supervised local scheduler operation is complete as opt-in local operation support, and PM-D5 through PM-D8 compatibility/debt fold-in slices are complete. PM-D8 completes the E1-R5 bridge canonical adapter fold-in in PR #491. O1F remains validation-only and O2/O3 do not add app-embedded, browser-owned, default-on, or independently mutation-authoritative scheduling.

## Wave 8 implementation evidence

- [MVP eval runner completion report](mvp/wave8/mvp_eval_runner_completion_report.md) — source PR #451. This is an operator-facing evaluation-flow convenience only and does not mark O2/O3 complete.

## Wave 7 implementation evidence

- [Wave 7 Cross-Slice Convergence Audit](architecture/wave7_cross_slice_convergence_audit.md)
- [E1-R3 provenance-preserving formation summary](architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md)
- [E1-R3 completion report](mvp/wave7/e1r3_completion_report.md)
- [E1-R4 retrieval-response grounding](architecture/e1r4_retrieval_response_grounding.md)
- [E1-R4 completion report](mvp/wave7/e1r4_completion_report.md)
- [E1-R5 Primary MEM recall candidate discovery bridge](architecture/e1r5_primary_mem_recall_candidate_bridge.md)
- [E1-R5 completion report](mvp/wave7/e1r5_completion_report.md)
- [E1-R5 Post-Wave-7 Correction Convergence Audit](architecture/e1r5_post_wave7_correction_convergence_audit.md)

## Wave 6 implementation evidence

- [Wave 6 Cross-Slice Convergence Audit](architecture/wave6_cross_slice_convergence_audit.md)
- [O1F completion report](mvp/wave6/o1f_completion_report.md)
- [I-5B completion report](mvp/wave6/i5b_completion_report.md)
- [I-7C completion report](mvp/wave6/i7c_completion_report.md)
- [E1-R1 completion report](mvp/wave6/e1r1_completion_report.md)
- [E1-R2 completion report](mvp/wave6/e1r2_completion_report.md)
- [O1F operational validation](architecture/o1f_operational_validation.md)
- [Phase I-5B Pin / Unpin apply and ranking behavior](architecture/phase_i5b_pin_unpin_apply.md)
- [Phase I-7C Held Apply / Discard runtime governance](architecture/phase_i7c_held_apply_discard_runtime.md)
- [E1-R1 trusted Home scene admission](architecture/e1r1_trusted_home_scene_admission.md)
- [E1-R2 character-store bootstrap command](architecture/e1r2_character_store_bootstrap.md)

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

## Offline tooling and runbooks

- [Twin Extraction prompt specification](tools/twin_extraction_prompts.md) — caller-invoked, bounded, runtime-non-contact offline material-extraction prompts and tooling notes.
- [Twin Extraction runbook](tools/twin_extraction_runbook.md) — execution steps for the offline preprocessing/batch-runner/merge CLIs. This tooling does not connect to MEM/SOUL bootstrap or the RelaySLP pipeline.

## Target architecture and post-MVP design

- [File-first Character Workspace design](architecture/file_first_character_workspace_design.md)
- [RelayREL relationship design](architecture/relayrel_relationship_design.md)
- [Character template creation flow](architecture/character_template_creation_flow.md)
- [Character belief, relationship, and social expression dynamics](architecture/character_belief_relationship_dynamics_design.md)
- [ADR: character-conditioned belief without rewriting observation](adr/character_conditioned_belief_model.md)
- [Experimental SOUL replacement and memory bootstrap](relaysoul/experimental_soul_replacement_memory_bootstrap_design.md)

These documents are target architecture unless explicitly listed as a current completed boundary above. Experimental SOUL replacement is explicitly post-MVP and does not alter the ordinary Phase I-9 revision/rollback path.

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
