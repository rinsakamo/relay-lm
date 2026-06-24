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
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
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
  A0 through A2: complete
  B0 through B3: complete
  I1-B ordinary request-runtime enqueue/source capture: complete
  C1-0 through C1-5: complete
  Phase 6-C2 one-job claim/rehydrate/execute adapter: complete

RelayMEM Primary integration:
  M1/M2 store and retrieval foundations: complete
  M3a-M3h Primary MEM formation/persistence primitives: complete
  I1 next-turn Primary MEM recall: complete
  character and namespace isolation: complete
  I1-G pre-enqueue background-finalizer durability: unresolved

SOUL Lab:
  UI-A0 through UI-A7: complete
  I2 real latest-run and memory observation: complete
  I3 I3 auditable Primary MEM Correct: complete
  broader authoritative mutations: pending

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

Phase 6-C2 one-job claim/rehydrate/execute adapter: complete. It accepts one exact queued canonical record, uses B3 claim, resolves source through C1-5, invokes C1-2, and preserves bounded retry/terminal behavior without adding a queue scanner, daemon, generalized worker pool, or retry scheduler.

Phase I-1 next-turn recall and scope isolation are complete. Phase I-2 real SOUL Lab observation is complete. Phase I-3 auditable Correct is the next product boundary.

## Completed Primary MEM end-to-end loop

```text
finalized user turn
  -> deferred SLP admission and durable enqueue       complete as I1-B
  -> durable protected source publication             complete as C1-5
  -> B3 queue claim and active lease                  complete helper boundary
  -> C2 one-job claim/rehydrate/execute adapter        complete
  -> exact C1-0 protected source                      complete
  -> C1-2 one-claimed worker execution                complete
  -> C1-1 RelayMEM M3a-M3h processing                 complete
  -> C1-3 outcome classification                      complete
  -> C1-4 fault/crash convergence                     complete
  -> B3 retry release or terminal commit              complete
  -> durable page/index/log result                    complete
  -> next-turn RelayMEM retrieval                      complete as Phase I-1
  -> RelayCTX bounded injection                        complete as Phase I-1
  -> model response uses the formed memory             complete as Phase I-1
  -> SOUL Lab reads real latest-run and memory outcome complete as Phase I-2
```

### I1-A: B3 queue lifecycle — complete

B3 implements claim, lease renewal, retry release, stale recovery, and terminal commit. It owns queue control only. It preserves dispatch-idempotency ownership, uses revision/owner/generation/token fencing, exposes content-free diagnostics, never generates `dead_letter`, and never schedules or executes a worker by itself.

### I1-B: request-runtime deferred enqueue — complete

Ordinary managed non-stream and stream finalization runs the exact A1 -> A2 -> B1 -> B2 sequence after visible response delivery.

Current guarantees:

- visible response success is independent of deferred persistence,
- exact runtime-private artifacts pass between stages,
- default-off and dry-run-first rollout remains,
- no inline B3 claim, worker execution, or RelayMEM persistence,
- C1-5 commits the protected source before B2 publishes the content-free queue record,
- the process-local registry is an optional bounded hot cache,
- claim-time preparation builds a fresh C1-0 source and one-shot scope.

C1-5 makes protected-source recovery restart-complete for durably enqueued jobs. It does not close the earlier process-exit window before source publication and B2 enqueue; that is I1-G.

### I1-C: Primary MEM worker and C2 integration — complete

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

### I1-D: next-turn recall and isolation — complete

Phase I-1 proves:

1. a first ordinary turn forms durable Primary MEM through C2,
2. a second ordinary turn discovers it through existing M2,
3. canonical Primary page and index/log validation succeeds,
4. exact character partition and namespace isolation are enforced,
5. only bounded selected memory is injected through RelayCTX,
6. backend-bound context contains the selected memory,
7. response generation completes using that path,
8. wrong-character and wrong-namespace requests do not observe the memory.

### I1-E / Phase I-2: real SOUL Lab observation — complete

Phase I-2 adds loopback-only, read-only observation of:

- the latest completed managed run,
- recently formed validated Primary memories,
- held and blocked worker outcomes,
- memories actually included in the latest backend-bound request.

The observation read model:

- preserves B3, C1-2/C1-3, M1/M2, M3a-M3h, RelayRUN, and RelayCTX authority,
- adds durable bounded receipts only where restart-safe evidence did not already exist,
- uses exact versioned schemas and strict browser validation,
- enforces character and namespace isolation,
- refuses non-loopback config or peer access,
- keeps real server data and explicit local preview data separate,
- exposes no raw prompt, transcript, trace, path, credential, queue/lease metadata, or full memory page,
- implements no mutation.

### I1-D: next-turn recall validation — complete

Phase I-1 completes next-turn recall and character/namespace isolation.

### I1-E / Phase I-2: real SOUL Lab observation — complete

Phase I-2 exposes bounded, loopback-only latest-run, formed, held/blocked, and actually injected memory evidence without changing RelayMEM, RelaySLP, RelayRUN, or RelayCTX authority.

### I1-G: pre-enqueue background-finalizer durability — unresolved

I1-G tracks termination after visible response delivery but before durable source and B2 queue publication. C1-5, C2, Phase I-1, and Phase I-2 do not close this boundary. `docs/config_schema.md`, the Current/Target matrix, and status smokes must move together; stale TODO or future-tense text in related documents is rejected.

## Active priority: Phase I-3 auditable Correct

Add one fully auditable `Correct` operation whose result changes later retrieval behavior while preserving prior state and provenance.

Required sequence:

```text
real observed memory item
  -> explicit character/namespace/current-memory validation
  -> bounded correction preflight
  -> atomic authoritative memory update
  -> durable audit evidence
  -> later M2 retrieval selects corrected representation
```

Phase I-3 does not include general memory administration, RelaySOUL mutation, queue scanning, scheduler/daemon lifecycle, or Secondary MEM consolidation. Forget, pin/unpin, merge, held apply/discard, and broader operations follow later.

## Current completion criteria

The end-to-end Primary MEM loop is complete through observation when:

- a managed turn schedules deferred Primary MEM processing without delaying visible output,
- the durable queue claims, leases, retries, recovers stale work, and reaches terminal state,
- ordinary queued work reaches C1-2 through C2,
- C1-5 restores protected source after restart for durably enqueued work,
- formed Primary MEM is retrieved in a later ordinary turn,
- character and namespace isolation are verified,
- SOUL Lab reads real latest-run and memory outcomes,
- observation survives restart without inventing missing evidence,
- duplicate/retry smoke preserves queue and memory-write idempotency.

The pre-enqueue background-finalizer crash window remains explicitly outside this completion claim.

## Current caveats

- Managed client-history exclusion remains default-off and dry-run-only by default.
- v1 instruction-bearing apply requires exact explicit provenance; active tool transactions remain blocked.
- C4b is diagnostics-only and does not semantically apply RelaySCN state.
- C5 requires a trusted in-process typed-parse source and does not parse arbitrary backend visible responses.
- RelayCTX stream suppression and TTS handoff metadata are default-off; RelayLM Core does not execute TTS/audio/avatar behavior.
- I1-G remains unresolved: I1-B is response-background-task based and the pre-enqueue process-exit window is not restart-complete.
- C1-5 protects only work that reached source publication and durable enqueue.
- Phase I-2 is observe-only; no Correct/forget/pin/merge/apply/discard behavior exists.
- Secondary MEM and actual RelaySOUL apply remain later work.

## Deferred after the current boundary

- RelayMEM-M4 Secondary MEM consolidation,
- broad SOUL proposal apply,
- generalized memory administration,
- queue scanner/scheduler and daemon/service lifecycle,
- static SOUL Lab bundle serving,
- TTS/audio/Live2D execution,
- protocol expansion,
- model-specific optimization,
- generalized agent functionality.

<!-- phase-i3-auditable-primary-mem-correct -->
## Phase I-3 auditable Primary MEM Correct — complete (2026-06-24)

Phase I-3 completes the first real observe/correct/retrieve loop. A formed Primary MEM observed through Phase I-2 can be corrected through read-only preflight, bounded semantic diff, explicit short-lived-token apply, immutable successor-page publication through the existing M3e boundary, canonical M3f/M3g index/log convergence, and immutable audit receipt finalization. Existing M2 retrieval resolves only the corrected current revision and existing RelayCTX injection remains the sole prompt path.

Character/namespace isolation, stable logical memory identity, no-clobber publication, exact operation idempotency, one-winner revision fencing, crash recovery, and historical used-memory integrity are preserved. Correction reason, audit receipt, paths, digests, lineage, queue/lease state, and prior full pages are not retrieval inputs or public prompt content.

Authority and exact contracts: `docs/architecture/phase_i3_auditable_primary_mem_correct.md`.

Still separate and unresolved: the I1-G process-exit window after visible-response delivery but before background-finalizer protected-source and B2 queue publication. Phase I-3 does not implement forget, pin/unpin, merge, held apply/discard, Secondary MEM consolidation, RelaySOUL mutation, queue scanner/scheduler/daemon, static UI serving, or TTS/audio/avatar execution.

