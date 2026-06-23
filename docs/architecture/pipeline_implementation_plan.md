---
relaylm_doc_type: implementation_plan
relaylm_authority: implementation_status_and_phase_sequencing
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - phase lands
  - sequencing changes
  - an integration milestone changes state
  - a target-only schema gains producer consumer apply skip block contract projection and smoke coverage
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical MVP authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - current_target_migration_guide.md
  - client_history_authority_contract.md
  - client_instruction_authority_contract.md
  - phase5_5_stream_unpack_bounded_slice.md
  - phase6_async_relayslp_bounded_slice.md
  - phase6a1_relayslp_job_admission_contract.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_primary_worker_outcome_classifier.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - soul_lab_ui_mvp.md
  - soul_lab_ui_a6_shared_shell_settings_handoff.md
  - soul_lab_ui_a7_management_projection_handoff.md
  - soul_lab_runtime_mvp.md
---
# RelayLM Pipeline Implementation Plan

## Purpose

This document owns implementation status, phase sequencing, dependency boundaries, and the active integration priority. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact contracts remain in their dedicated documents, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

The project is in an integration-first stage. New helper-only or mock-only slices are justified only when they directly unblock the active end-to-end milestone or close a demonstrated safety defect.

## Status legend

- **complete**: the bounded contract and intended helper or runtime wiring exist with smoke coverage.
- **integration pending**: component boundaries exist, but the ordinary runtime does not yet complete the user-visible loop.
- **planned**: design exists without a complete producer, consumer, apply, and validation path.
- **deferred**: intentionally not a gate for the active milestone.

## Current position

```text
Phase 5-C managed-route correctness:
  v0 no-instruction managed apply: complete
  v1 explicit-provenance instruction-bearing managed apply: complete
  C4b cache-hit RelaySCN-facing diagnostics projection: complete, diagnostics-only
  C5 runtime-private typed-parse / cache-writer plumbing: complete, default-off
  trusted backend-response artifact producer and RelaySCN semantic apply: pending

Phase 5-D pre-stream hardening: complete through D2

Phase 5.5 Stream Unpack / TTS handoff preparation:
  complete for RelayLM Core through B2 and C4
  adapter delivery and TTS/audio/avatar execution: pending outside Core

Phase 6 asynchronous RelaySLP orchestration:
  A0 ownership and sequencing: complete
  A1 job admission: complete
  A2 response-finalization handoff: complete
  B0 durable queue contract: complete
  B1 dispatch/job-record preflight: complete
  B2 atomic durable enqueue: complete
  B3 queue lifecycle helpers: complete
  I1-B ordinary request-runtime A1 -> A2 -> B1 -> B2 wiring: complete
  C1-0 protected worker-source bundle: complete
  C1-1 RelayMEM M3a-M3h compose: complete
  C1-3 pure worker-outcome classifier: complete
  C1-2 one-already-claimed-job worker execution: next

RelayMEM independent track:
  M1/M2 store and retrieval foundations: complete
  M3a-M3g Primary MEM formation and persistence primitives: complete
  M3h read-only reconciliation recovery audit: complete
  C1-1 exact M3a-M3h composition: complete
  ordinary-runtime claimed-worker integration and next-turn recall: pending

SOUL Lab UI independent track:
  UI-A0 through UI-A6 browser-local presentation slices: complete
  UI-A7 local-only settings/characters read projections: complete
  latest-run and memory-outcome reads: pending
  authoritative mutation APIs: pending

SOUL Lab Runtime:
  TTS/audio/avatar adapter execution: planned later
```

### Compatibility status anchors

Phase 6-B1 dry-run job-record and dispatch-idempotency preflight helper: complete.

Phase 6-B2 atomic durable enqueue: complete.

Phase 6-B3 queue lifecycle: complete.

Integration Milestone I1-B request-runtime deferred enqueue and protected source capture: complete for ordinary managed non-stream and stream requests.

Phase 6-C1-0 protected worker source, C1-1 RelayMEM composition, and C1-3 pure outcome classification: complete.

The next RelayLM Core boundary is C1-2: execute one already-claimed canonical B3 job under the exact active owner, claim-generation, lease-token, revision, and expiry fence. Scheduler loops, generalized worker pools, and restart-complete protected source persistence remain later boundaries.

## Active priority: Integration Milestone I1

### Primary MEM end-to-end runtime loop

The highest-priority implementation goal is one ordinary runtime loop that proves RelayLM's core product value:

```text
finalized user turn
  -> deferred SLP admission and durable enqueue       complete as I1-B
  -> B3 queue claim and active lease                  helper complete
  -> exact C1-0 protected source                      complete
  -> C1-2 one-claimed worker execution                next
  -> C1-1 RelayMEM M3a-M3h processing                 complete
  -> C1-3 outcome classification                      complete
  -> B3 retry release or terminal commit
  -> durable page/index/log result
  -> next-turn RelayMEM retrieval
  -> RelayCTX injection
  -> model response uses the formed memory
  -> SOUL Lab can inspect the result through a real API
```

This milestone has priority over Secondary MEM consolidation, additional mock UI surfaces, TTS/Live2D execution, new RelaySOUL governance documents, protocol expansion, and model-specific optimization.

### I1-A: Phase 6-B3 queue lifecycle — complete

The bounded direct helper implements:

```text
claim
renew_lease
retry_release
stale_recovery
commit_terminal
```

It preserves dispatch-idempotency ownership in Phase 6 / RelayRUN, uses revision/owner/claim-generation/lease-token fencing, classifies queue-control outcomes without deciding memory meaning, exposes only content-free public diagnostics, and keeps visible-response success independent of queue processing.

B3 remains default-off and dry-run-first. It validates complete canonical B2 records, uses a nonblocking queue lock and inode/byte compare-and-swap, never generates `dead_letter`, and never schedules or executes a worker by itself.

### I1-B: request-runtime deferred enqueue wiring — complete

Ordinary managed non-stream and stream response finalization now executes the exact A1 -> A2 -> B1 -> B2 sequence in a Starlette background task after visible response delivery. The implementation provides:

- visible response finalization independent of queue persistence,
- bounded enqueue/source-retention failure reporting without invalidating an already valid response,
- exact runtime-private artifact handoff between stages,
- default-off and dry-run-first rollout,
- content-free audit projection and leakage smoke,
- no inline B3 claim, worker execution, or RelayMEM persistence,
- B2-success-gated process-local protected source capture,
- exact claim-time C1-0 construction and one-shot consumption.

The first registry is capacity/TTL bounded and process-local. Capacity exhaustion rejects the new capture rather than evicting an existing one; TTL expiry removes the capture and later claim-time consumption returns explicit source-unavailable. It is not restart-complete.

A separate durability gap remains if the process exits after response delivery but before the background task completes. Restart completion must cover that pre-enqueue window as well as post-enqueue protected-source persistence.

### I1-C: Phase 6-C Primary MEM worker execution — integration pending

Completed bounded components:

- C1-0 exact protected worker-source schema, builder, validator, correlation, one-shot scope, and content-free projection,
- C1-1 exact M3a-M3h compose function with stage ledger and content-free projection,
- C1-3 pure M3e/M3g/M3h outcome classifier producing bounded B3 transition intent.

Remaining C1-2 worker path:

```text
B3 active lease fence
  -> exact C1-0 source consumption
  -> C1-1 M3a-M3h compose
  -> C1-3 pure outcome classification
  -> final active lease fence
  -> B3 retry release or terminal commit
```

The worker must:

- revalidate the exact active owner, claim generation, lease token, revision, and expiry before execution-sensitive transitions,
- never execute under an expired or stale lease,
- preserve the separation between dispatch idempotency and memory-write idempotency,
- invoke the existing C1-1 compose boundary rather than redefining M3 semantics,
- use the C1-3 classifier rather than duplicating outcome mapping,
- avoid direct RelaySOUL mutation and Secondary MEM consolidation,
- remain detached from visible response completion.

The first worker slice executes one already-claimed job. Scheduler loops, broad concurrency management, generalized worker pools, and retry-timing engines are not prerequisites for this boundary.

### I1-D: next-turn recall validation

Prove that a Primary MEM formed by the ordinary runtime can be selected by the existing RelayMEM retrieval path and injected by RelayCTX on a later turn.

Required integration smoke:

1. complete a first turn with an eligible governed experience,
2. enqueue and process one Primary MEM job,
3. verify durable page/index/log state,
4. submit a second turn whose answer requires that memory,
5. verify the selected memory is scoped to the correct character and namespace,
6. verify the backend-bound context includes only the bounded selected memory,
7. verify no cross-character or cross-namespace leakage,
8. verify duplicate dispatch and worker retry preserve both idempotency domains.

### I1-E: SOUL Lab real observation bridge

UI-A7 already provides the bounded local-only read foundation for settings and character-registry metadata. It does not expose run or memory outcomes.

After the runtime loop exists, add server-owned read APIs for:

- latest run and SLP status,
- recently formed memories,
- held or blocked memory outcomes,
- memories used in the latest concrete UI session or run.

The first mutation slice should be one fully auditable memory correction path. Forget, pin/unpin, merge, and broader held-memory operations follow after correction works end to end.

## I1 completion criteria

Integration Milestone I1 is complete only when all of the following are true:

- a normal managed turn can schedule deferred Primary MEM processing without delaying the visible response,
- the durable queue can claim, lease, retry, recover stale work, and reach terminal state,
- a worker can execute the existing M3a-M3h boundaries under an exact B3 lease,
- formed Primary MEM is retrieved in a later ordinary turn,
- character and namespace isolation are verified,
- SOUL Lab reads real latest-run and memory outcomes,
- at least one correction operation changes later retrieval behavior,
- restart and duplicate-dispatch smoke preserve idempotency.

I1-B and helper/component completion alone do not satisfy I1.

## Current caveats

- Managed client-history exclusion remains default-off and dry-run-only by default.
- v1 instruction-bearing apply requires exact explicit provenance; active tool transactions remain blocked.
- C4b is a diagnostics-only cache-hit projection and does not semantically apply RelaySCN state.
- C5 runtime writer plumbing requires a trusted in-process typed-parse source and does not parse backend visible responses.
- Current profile compilation still precedes normalized target SCN/INT/Retrieval handoffs.
- Complete Runtime Compile Gate v1 route-authority/fallback/source taxonomy is not implemented.
- RelayCTX stream suppression and TTS handoff metadata are default-off; RelayLM Core does not deliver transport or execute TTS/audio/avatar behavior.
- I1-B request-runtime enqueue/source capture is complete but process-local and response-background-task based, not restart-complete.
- C1-2 worker execution and autonomous worker invocation of RelayMEM M3a-M3h are absent from `main`.
- SOUL Lab UI-A7 provides bounded local read management metadata but no real run/memory observation or authoritative mutation.
- RelayREF output observation, Secondary MEM consolidation, and actual RelaySOUL apply remain later work.
- Token estimation is deterministic and CJK-aware but model-agnostic rather than tokenizer-exact.

## Completed implementation groups

### Core request and context path

Complete bounded work includes PipelineContext stabilization, RelayCTX Repack, RelayINT compatibility, PipelineNodeResult, non-stream RelayCTX Unpack, managed client-history authority through v0/v1 apply, C4b cache-hit diagnostics projection, C5 runtime-private parse/writer plumbing, CJK-aware token estimation, and lazy RelayRUN recovery-detail wiring.

### Stream safety and handoff preparation

Phase 5.5 is closed for RelayLM Core through:

- stream sentinel observation,
- safe visible/internal suppression,
- request-runtime SSE wrapping,
- TTS-safe segmentation hints,
- runtime-private adapter handoff plans,
- adapter-facing transport-envelope construction.

Concrete adapter delivery and TTS/audio/avatar execution belong to SOUL Lab Runtime MVP and are deferred until the text and memory loop is proven.

### Phase 6 orchestration and worker components

Phase 6 has implemented exact bounded artifacts through B3 fenced queue lifecycle and I1-B ordinary request-runtime enqueue/source capture. B2 persists a queued record. B3 can claim, renew, retry-release, recover stale work, and commit terminal state. C1-0 provides the exact protected worker source, C1-1 composes M3a-M3h, and C1-3 classifies exact outcomes. C1-2 remains the missing connection for one already-claimed job; no scheduler or worker pool is implied by I1-B.

### Primary MEM primitives

RelayMEM M3a-M3h provide formation, lineage, deterministic page construction, atomic page publication, index/log reconciliation, and read-only recovery classification. C1-1 now fixes their exact composition order without weakening stage validators. They remain disconnected from autonomous queued execution until C1-2 lands.

### SOUL Lab presentation and read foundation

UI-A0 through UI-A6 provide the shared shell, Home, Adoption, Communication, Pod, Memory Inspector, Settings, localization, theme, active-character scope, and bounded browser-local operation previews.

UI-A7 adds loopback-only, secret-free `GET /lab/api/settings` and `GET /lab/api/characters` projections with exact browser schema validation and explicit mock fallback. It does not prove real memory observation or durable mutation.

## Deferred until after I1

The following are not active blockers for I1:

- RelayMEM-M4 Secondary MEM consolidation,
- broad SOUL proposal apply/rollback execution,
- additional mock-only SOUL Lab screens,
- TTS, audio queues, Live2D/avatar control, lip-sync, or OBS integration,
- `/v1/responses` or other protocol expansion,
- model-specific tokenizer integration,
- generalized agent/tool orchestration,
- large benchmark tournaments.

Small evaluation hooks required to validate I1 are not deferred. The integration smoke must record bounded latency, duplicate/retry behavior, recall success, and isolation failures.

## Sequencing rule

Independent tracks may still proceed in parallel when they do not conflict, but their local next slice must serve the active integration milestone. The project must not interpret track independence as permission to indefinitely postpone runtime wiring.

When a choice exists between:

```text
another isolated helper or mock projection
```

and:

```text
connecting an already implemented producer to its real consumer
```

choose the integration work unless a concrete safety defect blocks it.

## Update rule

Update this plan whenever a phase lands, I1 sequencing changes, a target-only schema gains a real producer/consumer path, or a mock/direct-helper boundary becomes ordinary runtime behavior. Any PR that marks a bounded handoff `current` and implemented must also review and update `docs/PROJECT_STATUS.md`, this plan, `docs/README.md`, the relevant architecture index entry, and any affected current/target boundary document in the same PR or explicitly document why no status change occurred. Keep detailed schema and historical evidence in dedicated contract and handoff documents rather than duplicating them here.
