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
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - integration_i1_primary_mem_two_turn_recall.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_a7_management_projection_handoff.md
  - soul_lab_runtime_mvp.md
---
# RelayLM Pipeline Implementation Plan

## Purpose

This document owns implementation status, phase sequencing, dependency boundaries, and the active integration priority. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact contracts remain in dedicated documents, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

The project is integration-first. New helper-only or mock-only slices are justified only when they directly unblock the active end-to-end milestone or close a demonstrated safety defect.

## Status legend

- **complete**: the bounded contract and intended helper/runtime wiring exist with smoke coverage.
- **integration pending**: component boundaries exist, but the ordinary runtime does not complete the intended loop.
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
  C1-2 one-already-claimed-job worker execution: complete
  C1-3 pure worker-outcome classifier: complete
  C1-4 integrated worker fault/crash convergence: complete
  C1-5 durable protected source persistence: complete
  Phase 6-C2 one-job claim/rehydrate/execute adapter: complete
  Phase I-1 next-turn Primary MEM recall: complete
  character and namespace isolation: complete
  I1-G pre-enqueue background-finalizer durability: unresolved

RelayMEM independent track:
  M1/M2 store and retrieval foundations: complete
  M3a-M3h Primary MEM formation/persistence primitives: complete
  C1-1/C1-2 execution boundary: complete
  C1-4 fault convergence: complete
  C1-5 protected-source restart recovery: complete
  C2 one-job runtime adapter: complete
  M3i-c next-turn recall and scope isolation: complete
  M4 Secondary MEM: deferred until I1 closes

SOUL Lab UI independent track:
  UI-A0 through UI-A7: complete
  real latest-run and memory-outcome reads: next product boundary
  authoritative mutation APIs: pending

SOUL Lab Runtime:
  TTS/audio/avatar adapter execution: planned later
```

## Compatibility status anchors

Phase 6-B1 dry-run dispatch/job-record preflight, B2 atomic durable enqueue, and B3 fenced queue lifecycle are complete.

Integration Milestone I1-B ordinary managed non-stream/stream deferred enqueue is complete.

Phase 6-C1-0 through C1-5 are complete:

- exact current-claim protected source,
- exact M3a-M3h composition,
- one-active-claim execution,
- pure outcome classification,
- integrated crash/fault convergence,
- durable claim-independent protected capture and restart rehydration.

Phase 6-C2 completes the thin one-job claim/rehydrate/execute integration adapter. It accepts one exact queued canonical record, uses B3 claim, resolves source through C1-5, invokes C1-2, and preserves bounded retry/terminal behavior without adding a queue scanner, daemon, generalized worker pool, or retry scheduler.

Phase I-1 completes next-turn recall and character/namespace isolation. The completed recall path is not a remaining migration item.

## Active priority: Integration Milestone I1

### Primary MEM end-to-end runtime loop

```text
finalized user turn
  -> deferred SLP admission and durable enqueue       complete as I1-B
  -> durable protected source publication             complete as C1-5
  -> B3 queue claim and active lease                  helper complete
  -> C2 one-job claim/rehydrate/execute adapter       complete
  -> exact C1-0 protected source                      complete
  -> C1-2 one-claimed worker execution                complete
  -> C1-1 RelayMEM M3a-M3h processing                 complete
  -> C1-3 outcome classification                      complete
  -> C1-4 fault/crash convergence                     complete
  -> B3 retry release or terminal commit              complete in bounded path
  -> durable page/index/log result                    complete in bounded path
  -> next-turn RelayMEM retrieval                     complete as Phase I-1
  -> RelayCTX bounded injection                       complete as Phase I-1
  -> model response uses the formed memory            complete as Phase I-1
  -> SOUL Lab reads real latest-run and memory outcome
  -> one auditable correction changes later retrieval
  -> pre-enqueue finalizer durability is resolved or explicitly bounded
```

This milestone has priority over Secondary MEM consolidation, additional mock UI, TTS/Live2D execution, broad RelaySOUL expansion, protocol expansion, and model-specific optimization.

### I1-A: Phase 6-B3 queue lifecycle — complete

B3 implements:

```text
claim
renew_lease
retry_release
stale_recovery
commit_terminal
```

It owns queue control only. It preserves dispatch-idempotency ownership, uses revision/owner/generation/token fencing, exposes content-free diagnostics, never generates `dead_letter`, and never schedules or executes a worker by itself.

### I1-B: request-runtime deferred enqueue — complete

Ordinary managed non-stream and stream finalization runs the exact A1 -> A2 -> B1 -> B2 sequence after visible response delivery.

Current guarantees:

- visible response success is independent of deferred persistence,
- exact runtime-private artifacts pass between stages,
- default-off and dry-run-first rollout remains,
- no inline B3 claim, worker execution, or RelayMEM persistence,
- C1-5 commits the protected source before B2 publishes the content-free queue record,
- the process-local registry is an optional capacity/TTL-bounded hot cache,
- claim-time preparation builds a fresh C1-0 source and one-shot scope.

C1-5 makes protected-source recovery restart-complete for durably enqueued jobs. It does not close the earlier process-exit window before source publication and B2 enqueue; that is I1-G.

### I1-C: Phase 6-C Primary MEM worker — complete for bounded one-job execution

Completed components:

- C1-0 exact source schema, builder, validator, correlation, scope, and projection,
- C1-1 exact M3a-M3h compose and stage ledger,
- C1-2 one already-claimed job worker with lease checkpoints and bounded retry timing,
- C1-3 pure outcome classifier,
- C1-4 lease-loss, crash-convergence, lock-contention, stale-claim, corruption, race, and leakage smoke,
- C1-5 durable protected capture, restart lookup, fresh-source construction, retention, and post-terminal cleanup,
- C2 exact queued-record claim, canonical reread, C1-5 preparation, unchanged C1-2 execution, and terminal-only cleanup.

```text
one exact queued canonical B3 record
  -> canonical B3 claim
  -> C1-5 protected capture lookup
  -> fresh C1-0 source and one-shot scope
  -> C1-2 one-claimed worker
  -> canonical B3 retry release or terminal commit
```

The C2 adapter does not scan the queue, own a daemon lifecycle, create a worker pool, sleep until retry time, or redefine RelayMEM semantics.

### I1-D: next-turn recall validation — complete

Phase I-1 proves that a Primary MEM formed by the ordinary runtime is selected by the existing RelayMEM retrieval path and injected by RelayCTX on a later turn.

Completed smoke:

1. completed a first turn with eligible governed experience,
2. published the protected source and enqueued one job,
3. claimed and executed it through the one-job adapter,
4. verified durable page/index/log state and B3 outcome,
5. submitted a second turn whose answer requires that memory,
6. verified correct character and namespace scope,
7. verified backend-bound context contains only bounded selected memory,
8. verified no cross-character or cross-namespace leakage,
9. verified duplicate dispatch and worker retry preserve both idempotency domains.

The implementation reuses existing M2 discovery and RelayCTX injection rather than adding a parallel retriever.

### I1-E: SOUL Lab real observation bridge

Status: next product boundary.

Add server-owned loopback-only read APIs for:

- latest run and SLP status,
- recently formed memories,
- held or blocked outcomes,
- memories used in the latest concrete run/session.

UI-A7 provides the bounded settings/characters read foundation only. Observation receipts, when needed, are read-model evidence and do not replace RelayMEM/RelaySLP/RelayCTX authority.

### I1-F: first auditable correction

Status: pending after real observation.

Add one fully auditable `Correct` operation whose result changes later retrieval behavior while preserving prior state and provenance. Forget, pin/unpin, merge, and broader held-memory operations follow later.

### I1-G: pre-enqueue background-finalizer durability

Status: unresolved required I1 correctness boundary.

I1-B currently schedules source publication and B2 enqueue in a Starlette background finalizer after visible response delivery. C1-5 is restart-complete only after the protected source has been durably published and the queue record exists. A process exit in the earlier response-to-publication window can still lose that turn's deferred work.

The accepted contract must define authority and recovery behavior for that window without moving M3a-M3h inline or making visible response success depend on memory persistence.

Required smoke must cover at least:

1. termination after visible response completion but before protected-source publication,
2. termination after protected-source publication but before B2 queue publication,
3. restart discovery or explicit accepted-loss classification without duplicate dispatch,
4. preservation of response independence, content-free queue records, and protected-source confidentiality,
5. idempotent convergence when the finalizer or recovery path is replayed.

Queue scanning, retry scheduling, and daemon lifecycle remain separate operational work unless the selected I1-G contract explicitly requires a minimal recovery enumerator.

## I1 completion criteria

I1 is complete only when:

- a managed turn schedules deferred Primary MEM processing without delaying visible output,
- the durable queue claims, leases, retries, recovers stale work, and reaches terminal state,
- ordinary queued work reaches C1-2 through the bounded one-job adapter,
- C1-5 restores protected source after restart for durably enqueued work,
- formed Primary MEM is retrieved in a later ordinary turn,
- character and namespace isolation are verified,
- SOUL Lab reads real latest-run and memory outcomes,
- at least one correction changes later retrieval behavior,
- duplicate/retry smoke preserves queue and memory-write idempotency,
- I1-G is resolved or bounded by an accepted explicit contract.

Component completion alone does not satisfy I1.

## Current caveats

- Managed client-history exclusion remains default-off and dry-run-only by default.
- v1 instruction-bearing apply requires exact explicit provenance; active tool transactions remain blocked.
- C4b is diagnostics-only and does not semantically apply RelaySCN state.
- C5 requires a trusted in-process typed-parse source and does not parse arbitrary backend visible responses.
- RelayCTX stream suppression and TTS handoff metadata are default-off; RelayLM Core does not execute TTS/audio/avatar behavior.
- I1-G remains unresolved: I1-B is response-background-task based and the pre-enqueue process-exit window is not restart-complete.
- C1-5 protects only work that reached source publication and durable enqueue.
- Phase I-1 proves later-turn recall and character/namespace isolation; it does not prove Lab observation or mutation.
- UI-A7 has no authoritative mutation.
- Secondary MEM and actual RelaySOUL apply remain later work.

## Completed implementation groups

### Core request and context path

Complete bounded work includes PipelineContext stabilization, RelayCTX Repack/Unpack foundations, RelayINT compatibility, managed client-history v0/v1 apply, C4b diagnostics projection, C5 parse/writer plumbing, CJK-aware token estimation, and lazy RelayRUN recovery-detail wiring.

### Stream safety and handoff preparation

Phase 5.5 is closed for RelayLM Core through stream sentinel observation, safe visible/internal suppression, request-runtime SSE wrapping, TTS-safe segmentation hints, runtime-private handoff plans, and adapter-facing transport-envelope construction.

### Phase 6 orchestration and worker components

Phase 6 has implemented B0-B3, I1-B, C1-0 through C1-5, the bounded C2 queued-record claim/rehydrate/execute adapter, and Phase I-1 scoped next-turn recall.

### Primary MEM primitives

RelayMEM M3a-M3h provide formation, lineage, deterministic page construction, atomic publication, index/log reconciliation, and read-only recovery classification. Their direct/helper semantics remain authoritative and are not redefined by Phase 6.

### SOUL Lab presentation and read foundation

UI-A0 through UI-A7 provide the browser shell, local mock product flows, Memory Inspector previews, and loopback-only settings/characters reads. Real observation is I1-E; durable correction is I1-F.

## Deferred until after I1

- RelayMEM-M4 Secondary MEM consolidation,
- broad SOUL proposal apply/rollback,
- additional mock-only SOUL Lab screens,
- TTS/audio/Live2D/avatar execution,
- `/v1/responses` and protocol expansion,
- model-specific tokenizer integration,
- generalized agent/tool orchestration,
- large benchmark tournaments.

Small evaluation hooks required to validate I1 are not deferred.

## Sequencing rule

Independent tracks may proceed in parallel only when their next slice serves I1 or closes a concrete safety defect. Prefer connecting an implemented producer to its real consumer over adding another isolated helper or mock projection.

## Update rule

Update this plan whenever a phase lands, I1 sequencing changes, a target-only schema gains a real producer/consumer path, or a helper/mock boundary becomes ordinary runtime behavior.

The same PR must review:

- `docs/PROJECT_STATUS.md`,
- `docs/README.md`,
- `docs/architecture/README.md`,
- `docs/config_schema.md`,
- the Boundary Matrix and affected sections of `current_target_migration_guide.md`,
- affected current/target and component plans,
- stale TODO or future-tense text in related documents,
- status-checking smoke scripts and their workflow path filters.

## Phase I-1 Primary MEM next-turn recall — complete

Phase 6-C1-0 through C1-5 are complete. Phase 6-C2 one-job claim/rehydrate/execute is complete. Phase I-1 next-turn Primary MEM recall and character/namespace isolation are complete.

Turn 2 uses the configured root's opaque character partition, existing M2 selection, strict Primary page/index/log/namespace verification, and existing RelayCTX bounded snippet injection. It does not introduce a parallel retriever or synchronously wait for the Turn 1 worker.
