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

Architecture documents follow the [AI-first documentation model](../DOCUMENTATION_MODEL.md). Treat document front matter as the first signal for type, authority, status, volatility, and non-authoritative scope when reading a file through partial search.

Canonical authority:

1. [Pipeline Responsibility Design](pipeline_responsibility_design.md)
2. [Pipeline Implementation Plan](pipeline_implementation_plan.md)
3. Dedicated current contracts
4. [Current / Target / Migration Guide](current_target_migration_guide.md)

Product-critical Phase 6 boundaries:

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
- [Phase 6-C1-3 Primary Worker Outcome Classifier](phase6c1_primary_worker_outcome_classifier.md)
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md)

Phase 6-A1 validates deferred RelaySLP admission metadata. Phase 6-A2 creates one runtime-private dry-run enqueue candidate after a finalized `turn_end`. Phase 6-B0 owns the durable-record, dispatch-idempotency, state-machine, duplicate/collision, lease/restart/corruption, and content-free projection contract. Phase 6-B1 generates deterministic dispatch/job identities and a runtime-private initial queued durable-job candidate without queue I/O. Phase 6-B2 performs gated atomic create-if-absent durable enqueue. Phase 6-B3 performs fenced claim, renewal, retry release, stale recovery, and terminal commit without worker execution. I1-B now wires ordinary managed non-stream and stream response finalization to post-response A1 -> A2 -> B1 -> B2 enqueue plus process-local protected source capture. Phase 6-C1 defines the exact active-lease, protected-source, idempotency, retry, crash, and outcome-mapping contract. C1-0 implements the exact request-local protected worker-source bundle, C1-1 implements the canonical M3a-M3h compose boundary, and C1-3 implements the pure queue-transition outcome classifier. C1-2 one-already-claimed-job worker execution is the remaining Phase 6-C1 runtime boundary on `main`.

Completed Core streaming boundary:

- [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md)

Phase 5.5 is complete for RelayLM Core. Concrete TTS execution, audio queueing, adapter delivery, Live2D/avatar mapping, motion, and lip-sync remain SOUL Lab Runtime MVP responsibilities.

Memory lifecycle:

- [Memory Lifecycle Design](memory_lifecycle_design.md) — short-term CTX, governed experience evidence, autonomous ordinary MEM formation, RelaySLP, and SOUL Lab memory operations.
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md) — current runtime enqueue/source-capture, queue lifecycle, C1 component, and remaining worker integration boundary.
- [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md) — independent MEM-M bounded implementation track for store contracts, retrieval usability, primary memory formation, secondary consolidation, and Lab-ready operations.

RelayMEM Primary persistence track:

- [RelayMEM-M3a Primary Formation Handoff](relaymem_m3a_primary_formation_handoff.md) — governed Primary MEM candidate boundary.
- [RelayMEM-M3d Primary Writer Handoff](relaymem_m3d_primary_writer_handoff.md) — exact M3c candidate/store-target revalidation and writer handoff.
- [RelayMEM-M3e Atomic Primary Page Writer](relaymem_m3e_atomic_primary_page_writer.md) — default-off direct-helper page publication.
- [RelayMEM-M3f Index/Log Reconciliation Preflight](relaymem_m3f_primary_index_log_reconciliation_preflight.md) — read-only deterministic reconciliation planning.
- [RelayMEM-M3g Index/Log Reconciliation Apply](relaymem_m3g_primary_index_log_reconciliation_apply.md) — gated index-before-log apply with exact-plan revalidation and retryable partial progress.
- [RelayMEM-M3h Reconciliation Recovery Audit](relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md) — exact-receipt read-only recovery classification and content-free projection.

SOUL Lab product layers:

- [SOUL Lab UI MVP](soul_lab_ui_mvp.md) — text-first Lab UI for character creation/adoption, Home, Communication, Lab Observation, and Pod / SOUL Intervention.
- [SOUL Lab UI-A0 / UI-A1 Handoff](soul_lab_ui_a0_a1_handoff.md) — current TypeScript/React/Vite foundation, mock Home, read-only Lab Observation preview, and browser authority boundary.
- [SOUL Lab UI-A2 Adoption Handoff](soul_lab_ui_a2_adoption_handoff.md) — first-launch No Active Character state, Lab Assistant guidance, and browser-local new/adopt/import draft flows.
- [SOUL Lab UI-A3 Communication Handoff](soul_lab_ui_a3_communication_handoff.md) — browser-local peer classification, autonomous mock exchange loop, Soft Stop, emergency stop, and content-free timeline.
- [SOUL Lab UI-A4 Pod Handoff](soul_lab_ui_a4_pod_handoff.md) — bounded intervention targets, locked protected traits, candidate diff, browser-local comparison, Hold/Discard, and non-executing Apply/Rollback previews.
- [SOUL Lab UI-A5 Memory Inspector Handoff](soul_lab_ui_a5_memory_inspector_handoff.md) — formed/held/blocked outcomes, bounded provenance, subjective perspective, formed-memory Forget/Pin/Unpin, held-candidate Discard, and shared Correct/Merge previews.
- [SOUL Lab UI-A6 Shared Shell / Settings Handoff](soul_lab_ui_a6_shared_shell_settings_handoff.md) — one shared shell owner, character-scoped route state, navigation-lock enforcement, and mock Settings authority boundaries.
- [SOUL Lab UI-A7 Read-only Management Projection Handoff](soul_lab_ui_a7_management_projection_handoff.md) — local-only secret-free runtime-config and character-registry reads, exact browser schema validation, and explicit mock fallback.
- [SOUL Lab Runtime MVP](soul_lab_runtime_mvp.md) — post-UI-MVP runtime adapter layer for TTS, audio queue, Live2D/avatar mapping, timing, preview, and adapter telemetry.

The current UI implementation is complete through UI-A7. UI-A7 adds only local-only read server management projections. Peer transport, settings and character mutations, persisted memory operations, RelaySOUL apply/rollback, static bundle serving, and Runtime adapter execution remain separate.

Current instruction-bearing actual apply uses `client_history_exclusion_apply.v1` with explicit `client_instruction_source.v1` provenance. Role, wording, and message position alone are not provenance.

Historical and MVP documents do not override these current owners.

Implementation handoffs under this directory are bounded slice records. Their front matter controls interpretation: `current` handoffs may describe a live bounded implementation until superseded, while `historical_after_merge` handoffs are implementation evidence only. Neither overrides Project Status, the implementation plan, or dedicated current contracts.
