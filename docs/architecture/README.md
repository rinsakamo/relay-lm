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

Use [Documentation index](../README.md) for the complete active map and [Project Status](../PROJECT_STATUS.md) for current implementation state.

## Canonical authority

1. [Pipeline Responsibility Design](pipeline_responsibility_design.md)
2. [Pipeline Implementation Plan](pipeline_implementation_plan.md)
3. Dedicated current contracts and handoffs
4. [Current / Target / Migration Guide](current_target_migration_guide.md)

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
- [I1-G Durable-finalization Contract and Replay Boundary](i1g_pre_enqueue_durable_finalization_contract.md)
- [I1-GD Durable-finalization Retention and Isolation Cleanup](i1gd_durable_finalization_retention_cleanup.md)
- [Integration I1 Primary MEM Two-Turn Recall](integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-2 Real SOUL Lab Observation](phase_i2_real_soul_lab_observation.md)
- [Phase I-3 Auditable Primary MEM Correct](phase_i3_auditable_primary_mem_correct.md)
- [Phase I-4A Primary MEM Forget / Hide Contract](phase_i4_primary_mem_forget_hide_contract.md)
- [Phase I-4B Primary Current State and Shared Mutation Fence](phase_i4b_primary_current_state_shared_fence.md)
- [Phase I-4C1 Primary Forget Hidden-Successor Commit](phase_i4c1_primary_forget_hidden_successor.md)
- [Phase I-4C2 Primary Forget Recovery and Finalization](phase_i4c2_primary_forget_recovery_finalization.md)
- [SOUL Lab UI-B0 Real Home Conversation](soul_lab_ui_b0_real_home_conversation.md)
- [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md)
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md)
- [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md)

## Current operational alignment

Phase 6 is complete through C1-5 and C2. O0 is the default-off operator-invoked one-job caller. I1-GA defines the fault model, I1-GB publishes bounded restart evidence before protected visible release, and I1-GC provides the caller-selected one-record convergence authority through exact C1-5, exact B2, canonical downstream reread, and an immutable completion marker.

I1-GD provides bounded retention and isolation cleanup while preserving sealed-pending replay evidence, using the same per-record fence as I1-GC plus the existing I1-GB root mutation lock. I1-GE remains validation-only full process-exit/fresh-restart proof. O1A remains the pure replay-before-queue round/idle contract. O1B is complete for one bounded sealed-record replay-lane opportunity, and O1C is complete for one bounded queue-lane opportunity. O1D1 must accept the exact scheduler gates and run one production round without sleeping. O1D2 fairness/retry/backoff/jitter/pacing, O1E stale recovery/shutdown, O1F operational validation, supervision, and always-on operation remain incomplete.

Phase I-4A defines lifecycle semantics. I-4B implements the read-only resolver/shared-fence boundary. I-4C1 implements hidden-successor commit ownership. I-4C2 implements bounded prepared recovery, operation-scoped M3f/M3g convergence, exact replay, and tombstone finalization without changing ordinary M2/RelayCTX behavior. I-4D owns ordinary retrieval exclusion and read-only historical lifecycle projection only; I-4E and I-4F own API/UI and full validation.

## Memory lifecycle

- [Memory Lifecycle Design](memory_lifecycle_design.md)
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md)
- [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md)
- [Phase I-4A Primary MEM Forget / Hide Contract](phase_i4_primary_mem_forget_hide_contract.md)
- [Phase I-4B Primary Current State and Shared Mutation Fence](phase_i4b_primary_current_state_shared_fence.md)
- [Phase I-4C1 Primary Forget Hidden-Successor Commit](phase_i4c1_primary_forget_hidden_successor.md)
- [Phase I-4C2 Primary Forget Recovery and Finalization](phase_i4c2_primary_forget_recovery_finalization.md)

The completed observation/correction path does not make Forget product-complete. I-4D is the user-visible semantic commit because ordinary M2 and RelayCTX must exclude hidden, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, and prior physical revisions before snippet construction, while historical receipts remain immutable.

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
- [SOUL Lab Runtime MVP](soul_lab_runtime_mvp.md)

The browser owns no queue, scheduler, worker, filesystem, namespace, backend, credential, SOUL, or mutation authority. The Forget UI remains unimplemented.

## Character cognition and RelaySOUL targets

- [Character Belief, Relationship, and Social Expression Dynamics](character_belief_relationship_dynamics_design.md)
- [ADR: Character-conditioned Belief Without Rewriting Observation](../adr/character_conditioned_belief_model.md)
- [Experimental SOUL Replacement and Memory Bootstrap](../relaysoul/experimental_soul_replacement_memory_bootstrap_design.md)

These are target-only. Experimental SOUL replacement is post-MVP, non-destructive, and distinct from ordinary same-character RelaySOUL revision and rollback.

## Wave 3 boundary

- [Wave 2 cross-slice convergence audit](wave2_cross_slice_convergence_audit.md) freezes the independent Wave 3 inputs.
- I1-GE is validation-only and adds no durable or replay authority.
- I-4D owns retrieval-only lifecycle exclusion and historical lifecycle overlay.
- O1D1 owns accepted gates and one bounded `replay -> queue` production round, then returns without sleep.
- O1D2/O1E/O1F remain scheduling policy, recovery/shutdown, and operational validation.
