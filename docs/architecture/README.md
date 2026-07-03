---
relaylm_doc_type: documentation_index
relaylm_authority: architecture_documentation_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - architecture entry points change
  - canonical architecture authority changes
  - local handoff interpretation changes
relaylm_not_authoritative_for:
  - current runtime behavior
  - phase sequencing details
  - exact schema details
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelayLM Architecture Docs

Use [Documentation index](../README.md) for the complete active map, [Project Status](../PROJECT_STATUS.md) for current implementation state, and [Project Execution Plan](project_execution_plan.md) for MVP sequencing and post-MVP roadmap ordering.

## Canonical authority

1. [Project Status](../PROJECT_STATUS.md)
2. [Project Execution Plan](project_execution_plan.md)
3. [Pipeline Responsibility Design](pipeline_responsibility_design.md)
4. Dedicated current contracts and handoffs
5. [Current / Target / Migration Guide](current_target_migration_guide.md)

## Character workspace target architecture

- [File-first Character Workspace Design](file_first_character_workspace_design.md) defines the target Markdown source tree, RelayREL boundary, SLP-maintained scene/memory wiki model, and KV-cache-friendly context tiers.
- [RelayREL Relationship Design](relayrel_relationship_design.md) defines target-specific relationship state, `RELATIONSHIP.md`, `relationships/<target>.md`, and relationship-conditioned interaction policy.
- [Character Template and Creation Flow](character_template_creation_flow.md) defines Quick Create, Advanced Create, no-character startup, template import, and primary-user-fit finished showcase character policy.
- [Pinned Normal Memory Pages](pinned_normal_memory_pages.md) defines pinned normal memory as ordinary retrieval memory protected from ordinary RelaySLP maintenance.
- [P0 RelayREL / RelaySCN / RelayEMO Ordering Fix](p0_relayrel_relayscn_relayemo_ordering_fix.md) records the completed pre-Character-Workspace ordering boundary, which is complete only once app.py request-path rewiring is present and validation passes.
- [Pipeline Responsibility Design](pipeline_responsibility_design.md) defines component ownership and the target REL -> SCN -> EMO -> INT -> MEM -> CTX order.
- [Memory Lifecycle Design](memory_lifecycle_design.md) defines MEMORY.md, memory pages, SLP memory apply boundaries, and content-free projections.

## Execution and roadmap

- [Project Execution Plan](project_execution_plan.md)
- [Pipeline Implementation Plan](pipeline_implementation_plan.md) — compatibility stub
- [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md) — compatibility stub

## Product-critical Phase 6 and Integration boundaries

- [Phase 6 Asynchronous RelaySLP Bounded Slice](phase6_async_relayslp_bounded_slice.md)
- [Phase 6-A1 RelaySLP Job Admission Contract](phase6a1_relayslp_job_admission_contract.md)
- [Phase 6-A2 Response-Finalization Handoff](phase6a2_relayslp_response_handoff_contract.md)
- [Phase 6-B0 Durable Queue Contract](phase6b0_relayslp_durable_queue_contract.md)
- [Phase 6-B1 Dispatch Preflight](phase6b1_relayslp_dispatch_preflight.md)
- [Phase 6-B2 Atomic Durable Enqueue](phase6b2_relayslp_atomic_durable_enqueue.md)
- [Phase 6-B3 Fenced Queue State Helpers](phase6b3_relayslp_queue_state_helpers.md)
- [Phase 6 I1-B Runtime Enqueue and Protected Source Capture](phase6_i1b_runtime_enqueue_source_capture_handoff.md)
- [Phase 6-C1 Primary MEM Worker Contract](phase6c1_primary_mem_worker_contract.md)
- [Phase 6-C1-1 RelayMEM Primary Pipeline Compose](phase6c1_relaymem_primary_pipeline_compose.md)
- [Phase 6-C1-2 One-claimed Primary MEM Worker](phase6c1_one_claimed_primary_worker_handoff.md)
- [Phase 6-C1-3 Primary Worker Outcome Classifier](phase6c1_primary_worker_outcome_classifier.md)
- [Phase 6-C1-4 Integrated Worker Fault Smoke](phase6c1_integrated_worker_fault_smoke_handoff.md)
- [Phase 6-C1-5 Durable Protected Source Persistence](phase6c1_durable_protected_source_persistence.md)
- [Phase 6-C2 One Queued Primary Worker Integration](phase6c2_one_queued_primary_worker_integration.md)
- [O0 Local One-Job Runner](o0_local_one_job_runner.md)
- [O1A Two-Lane Scheduler and Idle Contract](o1a_two_lane_scheduler_contract.md)
- [O1B Sealed I1-G Replay Lane](o1b_sealed_i1g_replay_lane.md)
- [O1C Eligible B2/B3 Queue Lane](o1c_eligible_b2_queue_lane.md)
- [O1D1 Accepted Scheduler Gates and One Production Round](o1d1_production_scheduler_round.md)
- [O1D2 Deterministic Scheduler Policy](o1d2_scheduler_policy.md)
- [O1E Scheduler Operational Controls](o1e_scheduler_operational_controls.md)
- [O1F Operational Validation](o1f_operational_validation.md)
- [I1-G Durable-finalization Contract and Replay Boundary](i1g_pre_enqueue_durable_finalization_contract.md)
- [I1-GD Durable-finalization Retention and Isolation Cleanup](i1gd_durable_finalization_retention_cleanup.md)
- [I1-GE Durable-finalization Crash Validation](i1ge_durable_finalization_crash_validation.md)
- [Integration I1 Primary MEM Two-Turn Recall](integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-2 Real SOUL Lab Observation](phase_i2_real_soul_lab_observation.md)
- [Phase I-3 Auditable Primary MEM Correct](phase_i3_auditable_primary_mem_correct.md)
- [Phase I-4A Primary MEM Forget / Hide Contract](phase_i4_primary_mem_forget_hide_contract.md)
- [Phase I-4B Primary Current State and Shared Mutation Fence](phase_i4b_primary_current_state_shared_fence.md)
- [Phase I-4C1 Primary Forget Hidden-Successor Commit](phase_i4c1_primary_forget_hidden_successor.md)
- [Phase I-4C2 Primary Forget Recovery and Finalization](phase_i4c2_primary_forget_recovery_finalization.md)
- [Phase I-4D Primary Retrieval Exclusion](phase_i4d_primary_retrieval_exclusion.md)
- [Phase I-4E Forget API and SOUL Lab UI](phase_i4e_forget_api_ui.md)
- [Phase I-4F Forget Product Validation](phase_i4f_forget_validation.md)
- [Phase I-5A Pin / Unpin Contract](phase_i5_pin_unpin_contract.md)
- [Phase I-5B Pin / Unpin Apply](phase_i5b_pin_unpin_apply.md)
- [Phase I-7A/B Held Apply / Discard Contract](phase_i7ab_held_apply_discard_contract.md)
- [Phase I-7C Held Apply / Discard Runtime](phase_i7c_held_apply_discard_runtime.md)
- [E1 MVP Evaluation Evidence Consolidation](e1_evaluation_consolidation.md)
- [E1-R1 Trusted Home Scene Admission](e1r1_trusted_home_scene_admission.md)
- [E1-R2 Character Store Bootstrap](e1r2_character_store_bootstrap.md)
- [E1-R3 Provenance-Preserving Primary MEM Formation Summary](e1r3_provenance_preserving_primary_mem_formation_summary.md)
- [E1-R4 Retrieval-Response Grounding](e1r4_retrieval_response_grounding.md)
- [E1-R5 Primary MEM Recall Candidate Discovery Bridge](e1r5_primary_mem_recall_candidate_bridge.md)
- [E1-R5 Post-Wave-7 Correction Convergence Audit](e1r5_post_wave7_correction_convergence_audit.md)
- [Wave 3 Cross-Slice Convergence Audit](wave3_cross_slice_convergence_audit.md)
- [Wave 4 Cross-Slice Convergence Audit](wave4_cross_slice_convergence_audit.md)
- [Wave 5 Cross-Slice Convergence Audit](wave5_cross_slice_convergence_audit.md)
- [Wave 6 Cross-Slice Convergence Audit](wave6_cross_slice_convergence_audit.md)
- [Wave 7 Cross-Slice Convergence Audit](wave7_cross_slice_convergence_audit.md)
- [SOUL Lab UI-B0 Real Home Conversation](soul_lab_ui_b0_real_home_conversation.md)
- [SOUL Lab UI-B1A Lifecycle Visibility](soul_lab_ui_b1a_lifecycle_visibility.md)
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md)

## Memory lifecycle

- [File-first Character Workspace Design](file_first_character_workspace_design.md)
- [RelayREL Relationship Design](relayrel_relationship_design.md)
- [Pinned Normal Memory Pages](pinned_normal_memory_pages.md)
- [Memory Lifecycle Design](memory_lifecycle_design.md)
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md)
- [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md) — compatibility stub
- [Phase I-4A Primary MEM Forget / Hide Contract](phase_i4_primary_mem_forget_hide_contract.md)
- [Phase I-4B Primary Current State and Shared Mutation Fence](phase_i4b_primary_current_state_shared_fence.md)
- [Phase I-4C1 Primary Forget Hidden-Successor Commit](phase_i4c1_primary_forget_hidden_successor.md)
- [Phase I-4C2 Primary Forget Recovery and Finalization](phase_i4c2_primary_forget_recovery_finalization.md)
- [Phase I-4D Primary Retrieval Exclusion](phase_i4d_primary_retrieval_exclusion.md)
- [Phase I-4E Forget API and SOUL Lab UI](phase_i4e_forget_api_ui.md)
- [Phase I-4F Forget Product Validation](phase_i4f_forget_validation.md)
- [Phase I-5A Pin / Unpin Contract](phase_i5_pin_unpin_contract.md)
- [Phase I-5B Pin / Unpin Apply](phase_i5b_pin_unpin_apply.md)
- [Phase I-7A/B Held Apply / Discard Contract](phase_i7ab_held_apply_discard_contract.md)
- [Phase I-7C Held Apply / Discard Runtime](phase_i7c_held_apply_discard_runtime.md)
- [E1-R5 Primary MEM Recall Candidate Discovery Bridge](e1r5_primary_mem_recall_candidate_bridge.md)

The current Product and RelayMEM status is intentionally not summarized here. Read [Project Status](../PROJECT_STATUS.md) for current state and [Project Execution Plan](project_execution_plan.md) for MVP sequencing.

## SOUL Lab product layers

- [SOUL Lab UI MVP](soul_lab_ui_mvp.md)
- [SOUL Lab UI-A0 / UI-A1 Handoff](soul_lab_ui_a0_a1_handoff.md)
- [SOUL Lab UI-A2 Adoption Handoff](soul_lab_ui_a2_adoption_handoff.md)
- [SOUL Lab UI-A3 Communication Handoff](soul_lab_ui_a3_communication_handoff.md)
- [SOUL Lab UI-A4 Pod Handoff](soul_lab_ui_a4_pod_handoff.md)
- [SOUL Lab UI-A5 Memory Inspector Handoff](soul_lab_ui_a5_memory_inspector_handoff.md)
- [SOUL Lab UI-A6 Shared Shell / Settings Handoff](soul_lab_ui_a6_shared_shell_settings_handoff.md)
- [SOUL Lab UI-A7 Read-only Management Projection Handoff](soul_lab_ui_a7_management_projection_handoff.md)
- [Phase I-2 Real SOUL Lab Observation](phase_i2_real_soul_lab_observation.md)
- [Phase I-3 Auditable Primary MEM Correct](phase_i3_auditable_primary_mem_correct.md)
- [SOUL Lab UI-B0 Real Home Conversation](soul_lab_ui_b0_real_home_conversation.md)
- [Phase I-4E Forget API and SOUL Lab UI](phase_i4e_forget_api_ui.md)
- [Phase I-4F Forget Product Validation](phase_i4f_forget_validation.md)
- [SOUL Lab UI-B1A Lifecycle Visibility](soul_lab_ui_b1a_lifecycle_visibility.md)
- [Phase I-5B Pin / Unpin Apply](phase_i5b_pin_unpin_apply.md)
- [Phase I-7C Held Apply / Discard Runtime](phase_i7c_held_apply_discard_runtime.md)
- [E1 MVP Evaluation Evidence Consolidation](e1_evaluation_consolidation.md)
- [E1-R1 Trusted Home Scene Admission](e1r1_trusted_home_scene_admission.md)
- [E1-R2 Character Store Bootstrap](e1r2_character_store_bootstrap.md)
- [E1-R3 Provenance-Preserving Primary MEM Formation Summary](e1r3_provenance_preserving_primary_mem_formation_summary.md)
- [E1-R4 Retrieval-Response Grounding](e1r4_retrieval_response_grounding.md)
- [E1-R5 Primary MEM Recall Candidate Discovery Bridge](e1r5_primary_mem_recall_candidate_bridge.md)
- [SOUL Lab Runtime MVP](soul_lab_runtime_mvp.md)

The browser owns no queue, scheduler, worker, storage root, namespace, backend, SOUL, or route authority. Forget, Pin / Unpin, and Held Governance mutation boundaries remain in explicit loopback contracts and server-side authorities. E1-R1 trust is route-owned and never browser-owned. E1-R4 grounding remains request-side and never exposes runtime-private evidence in public diagnostics. E1-R5 bridge diagnostics remain content-free and do not expose scoped roots, namespaces, paths, digests, lineage, or runtime-private evidence.

## Wave 7 implementation evidence

- [Wave 7 Cross-Slice Convergence Audit](wave7_cross_slice_convergence_audit.md)
- [E1-R3 Provenance-Preserving Primary MEM Formation Summary](e1r3_provenance_preserving_primary_mem_formation_summary.md)
- [E1-R3 completion report](../mvp/wave7/e1r3_completion_report.md)
- [E1-R4 Retrieval-Response Grounding](e1r4_retrieval_response_grounding.md)
- [E1-R4 completion report](../mvp/wave7/e1r4_completion_report.md)
- [E1-R5 Primary MEM Recall Candidate Discovery Bridge](e1r5_primary_mem_recall_candidate_bridge.md)
- [E1-R5 completion report](../mvp/wave7/e1r5_completion_report.md)
- [E1-R5 Post-Wave-7 Correction Convergence Audit](e1r5_post_wave7_correction_convergence_audit.md)

## Wave 6 implementation evidence

- [Wave 6 Cross-Slice Convergence Audit](wave6_cross_slice_convergence_audit.md)
- [O1F completion report](../mvp/wave6/o1f_completion_report.md)
- [I-5B completion report](../mvp/wave6/i5b_completion_report.md)
- [I-7C completion report](../mvp/wave6/i7c_completion_report.md)
- [E1-R1 completion report](../mvp/wave6/e1r1_completion_report.md)
- [E1-R2 completion report](../mvp/wave6/e1r2_completion_report.md)
- [O1F Operational Validation](o1f_operational_validation.md)
- [Phase I-5B Pin / Unpin Apply](phase_i5b_pin_unpin_apply.md)
- [Phase I-7C Held Apply / Discard Runtime](phase_i7c_held_apply_discard_runtime.md)
- [E1-R1 Trusted Home Scene Admission](e1r1_trusted_home_scene_admission.md)
- [E1-R2 Character Store Bootstrap](e1r2_character_store_bootstrap.md)

## Wave 5 / E1 evaluation evidence

- [Wave 5 Cross-Slice Convergence Audit](wave5_cross_slice_convergence_audit.md)
- [O1E completion report](../mvp/wave5/o1e_completion_report.md)
- [I-4F completion report](../mvp/wave5/i4f_completion_report.md)
- [E1 completion report](../mvp/wave5/e1_completion_report.md)
- [O1E Scheduler Operational Controls](o1e_scheduler_operational_controls.md)
- [Phase I-4F Forget Product Validation](phase_i4f_forget_validation.md)
- [E1 MVP Evaluation Evidence Consolidation](e1_evaluation_consolidation.md)

## Wave 4 implementation evidence

- [Wave 4 Cross-Slice Convergence Audit](wave4_cross_slice_convergence_audit.md)
- [O1D2 completion report](../mvp/wave4/o1d2_completion_report.md)
- [I-4E completion report](../mvp/wave4/i4e_completion_report.md)
- [UI-B1A completion report](../mvp/wave4/ui_b1a_completion_report.md)
- [I-5A completion report](../mvp/wave4/i5a_completion_report.md)
- [I-7A/B completion report](../mvp/wave4/i7ab_completion_report.md)

## Evaluation evidence

- [E1 MVP Evaluation Evidence Consolidation](e1_evaluation_consolidation.md) records implemented E1-R1/E1-R2/E1-R3/E1-R4/E1-R5 evidence and the current conditional non-E1 remaining work.
- [E1 Local Runtime Evaluation](e1_local_runtime_evaluation_2026_06_25.md) records explicit trusted-scene formation through O0, separate real Home recall, and the original evidence inventory.

## Character cognition and RelaySOUL targets

- [File-first Character Workspace Design](file_first_character_workspace_design.md)
- [RelayREL Relationship Design](relayrel_relationship_design.md)
- [Character Template and Creation Flow](character_template_creation_flow.md)
- [Character Belief, Relationship, and Social Expression Dynamics](character_belief_relationship_dynamics_design.md)
- [ADR: Character-conditioned Belief Without Rewriting Observation](../adr/character_conditioned_belief_model.md)
