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

Phase 6-A1 validates deferred RelaySLP admission metadata. Phase 6-A2 creates one runtime-private dry-run enqueue candidate after a finalized `turn_end`. Phase 6-B0 owns the durable-record, dispatch-idempotency, state-machine, duplicate/collision, lease/restart/corruption, and content-free projection contract. Phase 6-B1 generates deterministic dispatch/job identities and a runtime-private initial queued durable-job candidate without queue I/O. Phase 6-B2 now performs gated atomic create-if-absent durable enqueue with duplicate/collision/corruption classification and no worker invocation. Phase 6-B3 claim/lease/retry/terminal helpers are next.

Completed Core streaming boundary:

- [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md)

Phase 5.5 is complete for RelayLM Core. Concrete TTS execution, audio queueing, adapter delivery, Live2D/avatar mapping, motion, and lip-sync remain SOUL Lab Runtime MVP responsibilities.

Memory lifecycle:

- [Memory Lifecycle Design](memory_lifecycle_design.md) — short-term CTX, governed experience evidence, autonomous ordinary MEM formation, RelaySLP, and SOUL Lab memory operations.
- [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md) — current read-only/helper state and the migration into deferred Phase 6 orchestration.
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
- [SOUL Lab Runtime MVP](soul_lab_runtime_mvp.md) — post-UI-MVP runtime adapter layer for TTS, audio queue, Live2D/avatar mapping, timing, preview, and adapter telemetry.

The current UI implementation is complete through UI-A5. Peer transport, server-side management APIs, persisted memory operations, RelaySOUL apply/rollback, and Runtime adapter execution remain separate.

Current instruction-bearing actual apply uses `client_history_exclusion_apply.v1` with explicit `client_instruction_source.v1` provenance. Role, wording, and message position alone are not provenance.

Historical and MVP documents do not override these current owners.

Implementation handoffs under this directory are bounded slice records. After merge, they are historical implementation evidence unless a current status page, implementation plan, or contract explicitly references their behavior as current.
