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

Use [Documentation index](../README.md) for the complete active document map.

Architecture documents follow the [AI-first documentation model](../DOCUMENTATION_MODEL.md). Treat front matter as the first signal for type, authority, status, volatility, and non-authoritative scope.

Canonical authority:

1. [Pipeline Responsibility Design](pipeline_responsibility_design.md)
2. [Pipeline Implementation Plan](pipeline_implementation_plan.md)
3. Dedicated current contracts
4. [Current / Target / Migration Guide](current_target_migration_guide.md)

## Product-critical Phase 6 and Integration boundaries

- [Phase 6 Asynchronous RelaySLP Bounded Slice](phase6_async_relayslp_bounded_slice.md)
- [Phase 6-A1 RelaySLP Job Admission Contract](phase6a1_relayslp_job_admission_contract.md)
- [Phase 6-A2 RelaySLP Response-Finalization Handoff Contract](phase6a2_relayslp_response_handoff_contract.md)
- [Phase 6-B0 RelaySLP Durable Queue Contract](phase6b0_relayslp_durable_queue_contract.md)
- [Phase 6-B1 RelaySLP Dispatch Preflight](phase6b1_relayslp_dispatch_preflight.md)
- [Phase 6-B2 RelaySLP Atomic Durable Enqueue](phase6b2_relayslp_atomic_durable_enqueue.md)
- [Phase 6-B3 RelaySLP Fenced Queue State Helpers](phase6b3_relayslp_queue_state_helpers.md)
- [Phase 6 I1-B Runtime Enqueue and Protected Source Capture](phase6_i1b_runtime_enqueue_source_capture_handoff.md)
- [Phase 6-C1 Primary MEM Worker Contract](phase6c1_primary_mem_worker_contract.md)
- [Phase 6-C1-1 RelayMEM Primary Pipeline Compose](phase6c1_relaymem_primary_pipeline_compose.md)
- [Phase 6-C1-2 One-claimed Primary MEM Worker](phase6c1_one_claimed_primary_worker_handoff.md)
- [Phase 6-C1-3 Primary Worker Outcome Classifier](phase6c1_primary_worker_outcome_classifier.md)
- [Phase 6-C1-4 Integrated Worker Fault Smoke](phase6c1_integrated_worker_fault_smoke_handoff.md)
- [Phase 6-C1-5 Durable Protected Source Persistence](phase6c1_durable_protected_source_persistence.md)
- [Phase 6-C2 One Queued Primary Worker Integration](phase6c2_one_queued_primary_worker_integration.md)
- [O0 Local One-Job Runner](o0_local_one_job_runner.md)
- [Integration I1 Primary MEM Two-Turn Recall](integration_i1_primary_mem_two_turn_recall.md)
- [Phase I-2 Real SOUL Lab Observation](phase_i2_real_soul_lab_observation.md)
- [Phase I-3 Auditable Primary MEM Correct](phase_i3_auditable_primary_mem_correct.md)
- [Phase I-4A Primary MEM Forget / Hide Contract](phase_i4_primary_mem_forget_hide_contract.md)
- [SOUL Lab UI-B0 Real Home Conversation](soul_lab_ui_b0_real_home_conversation.md)
- [I1-G Pre-enqueue Durable-finalization Contract and Fault Model](i1g_pre_enqueue_durable_finalization_contract.md)
- [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md)
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md)

Phase 6-A1/A2 and B0-B3 own deferred admission, finalized-turn handoff, durable queue publication, and fenced queue lifecycle. I1-B wires ordinary managed response finalization to post-response enqueue. C1-0 owns exact current-claim source construction, C1-1 composes M3a-M3h, C1-2 executes one already-claimed job, C1-3 classifies outcomes, C1-4 verifies integrated fault convergence, C1-5 durably persists and restart-rehydrates the claim-independent protected capture, and C2 connects one exact queued record through canonical claim, rehydrate, and C1-2 execution.

O0 is the thin local caller before C2. It performs bounded non-recursive discovery, deterministic selection of at most one currently eligible queued record, a secure canonical reread, and exact config-owned character/store resolution before delegating unchanged lifecycle and worker authority to C2/B3/C1-5/C1-2. It is default-off, operator-invoked, and one-shot; it does not define O1 scheduling, O2 service supervision, or O3 always-on operation.

Phase I-1 completes ordinary next-turn Primary MEM recall with exact character/namespace isolation and RelayCTX injection. Phase I-2 adds a bounded read-only observation model, loopback-only APIs, strict browser validation, and real Lab Observation rendering without changing RelayMEM, RelaySLP, RelayRUN, or RelayCTX authority. Phase I-3 completes auditable revision-fenced Correct and later corrected retrieval. UI-B0 adds a browser-local text-first client for the existing RelayLM Chat Completions path without adding a new routing, memory, SOUL, backend, or worker authority.

Phase I-4A defines the target Forget contract: Forget is the user-facing operation, `hidden` is the canonical retrieval-ineligible lifecycle state, and the Forget tombstone is the immutable runtime-private audit/recovery artifact. It selects an immutable hidden successor Primary page with revision `N+1` as lifecycle authority and requires one Correct/Forget shared revision fence plus one canonical current-state resolver. Production apply, M2 exclusion, historical lifecycle projection, and the SOUL Lab Forget UI remain unimplemented.

I1-GA defines the turn-scoped sealed durable-finalization contract and fault model. I1-GB implements bounded private base/segment/seal publication, canonical reread, exact A1/A2/B1 preparation, and non-stream/stream pre-release admission. I1-GC restart replay and completion convergence, I1-GD retention/cleanup, and I1-GE full production crash integration remain unimplemented.

The next planned work is documented in [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md). I1-GC through I1-GE, Phase I-4B through I-4F, O1/O2/O3 automatic and supervised operation, later memory governance, Secondary MEM, and RelaySOUL apply/rollback remain separate.

## Completed Core streaming boundary

- [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md)

Phase 5.5 is complete for RelayLM Core. Concrete TTS execution, audio queueing, adapter delivery, Live2D/avatar mapping, motion, and lip-sync remain SOUL Lab Runtime MVP responsibilities.

## Memory lifecycle

- [Memory Lifecycle Design](memory_lifecycle_design.md) — short-term CTX, governed experience evidence, autonomous ordinary MEM formation, RelaySLP, and SOUL Lab memory operations.
- [Phase I-4A Primary MEM Forget / Hide Contract](phase_i4_primary_mem_forget_hide_contract.md) — exact target lifecycle, revision, persistence, recovery, and retrieval-exclusion semantics.
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md) — current enqueue/source capture, queue lifecycle, completed C1-0 through C1-5, C2, O0, I-1 recall, I-2 observation, I-3 correction, and remaining migration boundaries.
- [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md) — store contracts, retrieval, Primary MEM formation, worker integration, recall, observation, Secondary consolidation, and Lab-ready operations.
- [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md) — planned I-4 through I-9 work slices, SOUL Lab conversation, operational phases, parallel development, and evaluation gates.
- [I1-G Pre-enqueue Durable-finalization Contract](i1g_pre_enqueue_durable_finalization_contract.md) — contract/fault model plus completed I1-GB publication boundary; restart replay remains I1-GC work.

## RelayMEM Primary persistence track

- [RelayMEM-M3a Primary Formation Handoff](relaymem_m3a_primary_formation_handoff.md)
- [RelayMEM-M3d Primary Writer Handoff](relaymem_m3d_primary_writer_handoff.md)
- [RelayMEM-M3e Atomic Primary Page Writer](relaymem_m3e_atomic_primary_page_writer.md)
- [RelayMEM-M3f Index/Log Reconciliation Preflight](relaymem_m3f_primary_index_log_reconciliation_preflight.md)
- [RelayMEM-M3g Index/Log Reconciliation Apply](relaymem_m3g_primary_index_log_reconciliation_apply.md)
- [RelayMEM-M3h Reconciliation Recovery Audit](relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md)

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
- [Phase I-4A Primary MEM Forget / Hide Contract](phase_i4_primary_mem_forget_hide_contract.md)
- [SOUL Lab UI-B0 Real Home Conversation](soul_lab_ui_b0_real_home_conversation.md)
- [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md)
- [SOUL Lab Runtime MVP](soul_lab_runtime_mvp.md)

The browser shell is complete through UI-A7, Phase I-2 real observation, Phase I-3 Correct, and UI-B0 real Home conversation. UI-B0 uses a single unambiguous server-projected route, same-origin non-stream/SSE transport, explicit Real Runtime versus Local Preview sessions, Stop/Retry/New Conversation controls, and stale response fencing. Phase I-4A changes no browser behavior. The Forget UI, broader memory operations, RelaySOUL apply/rollback, static bundle serving, peer transport, and TTS/avatar execution remain separate.

Current instruction-bearing actual apply uses `client_history_exclusion_apply.v1` with explicit `client_instruction_source.v1` provenance. Role, wording, and message position alone are not provenance.

Historical and MVP documents do not override current owners. Implementation handoffs are bounded slice records; they do not override Project Status, the implementation plan, or dedicated current contracts.

## Integration I1 through UI-B0 and O0

- [Primary MEM two-turn recall](integration_i1_primary_mem_two_turn_recall.md): ordinary Turn 1 durable formation, ordinary Turn 2 scoped M2 selection, canonical page/index/log validation, and bounded RelayCTX injection.
- [Real SOUL Lab observation](phase_i2_real_soul_lab_observation.md): latest completed run, validated formed memories, durable held/blocked outcomes, and actual backend-bound used-memory evidence, all read-only and character/namespace scoped.
- [Auditable Primary MEM Correct](phase_i3_auditable_primary_mem_correct.md): token-gated revision-fenced correction, immutable audit evidence, recovery convergence, and later corrected retrieval.
- [Primary MEM Forget / Hide target contract](phase_i4_primary_mem_forget_hide_contract.md): defined target only; no current runtime completion claim.
- [Real Home conversation](soul_lab_ui_b0_real_home_conversation.md): existing RelayLM Chat Completions transport exposed through a bounded browser-local experiment surface.
- [O0 local one-job runner](o0_local_one_job_runner.md): one operator invocation selects and delegates at most one eligible already-durable queued job.

## Operational alignment

O0 is complete only for explicit one-shot local operation. UI-B0 does not own I1-G durability, queue selection, or worker service authority. I1-GA defines the target/fault model and I1-GB implements pre-release evidence publication only. Phase I-4A defines lifecycle semantics only. I1-GC through I1-GE remaining durability work, Phase I-4B through I-4F implementation, O1 queue scanning/scheduling, O2 supervision, and O3 always-on lifecycle remain separate roadmap slices.
