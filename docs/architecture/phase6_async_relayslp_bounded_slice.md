---
relaylm_doc_type: implementation_plan
relaylm_authority: phase6_async_relayslp_bounded_slice
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6 RelaySLP slice lands
  - request-runtime enqueue wiring changes
  - queue lifecycle or worker semantics change
  - RelayMEM-M3 producer consumer boundary changes
  - RelayRUN retry checkpoint or idempotency ownership changes
relaylm_not_authoritative_for:
  - RelayMEM candidate semantic classification
  - exact durable MEM page index or log schemas
  - RelaySOUL approval or revision schemas
  - SOUL Lab runtime TTS audio or avatar execution
relaylm_related_authority:
  - pipeline_implementation_plan.md
  - phase6a1_relayslp_job_admission_contract.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - memory_lifecycle_design.md
  - relayrun_runtime_checkpoint_design.md
  - ../PROJECT_STATUS.md
---
# Phase 6 Asynchronous RelaySLP Bounded Slice

## Status

Phase 6 is implemented through I1-B, fenced B3 lifecycle, and Phase 6-C1-0 through C1-5.

```text
Phase 6-A0 ownership and sequencing: complete
Phase 6-A1 deferred job admission: complete
Phase 6-A2 response-finalization handoff: complete
Phase 6-B0 durable queue contract: complete
Phase 6-B1 dispatch/job-record preflight: complete
Phase 6-B2 atomic durable enqueue: complete
Phase 6-B3 claim/renew/retry/stale/terminal lifecycle: complete
I1-B request-runtime enqueue/source production: complete
Phase 6-C1-0 protected source: complete
Phase 6-C1-1 M3a-M3h compose: complete
Phase 6-C1-2 one-claimed worker: complete
Phase 6-C1-3 outcome classifier: complete
Phase 6-C1-4 integrated fault smoke: complete
Phase 6-C1-5 durable protected source: complete
Phase 6-C2 one-job claim/rehydrate/execute adapter: complete
```

Ordinary finalization can publish a protected source and enqueue without delaying visible output. C1-2 can execute one exact already-claimed job. No current scanner, daemon, or scheduler automatically selects queued work.

## Purpose

RelaySLP is the deferred memory compiler. It improves future memory after the normal response path and must not delay or invalidate an already valid visible response.

```text
completed finalized turn
  -> A1 admission
  -> A2 response handoff
  -> B1 dispatch and durable-record candidate
  -> C1-5 protected-source publication
  -> B2 durable enqueue
  -> B3 claim/lease/retry/stale/terminal lifecycle
  -> C1 worker invokes RelayMEM-owned processing
  -> future turns retrieve formed memory
```

## Ownership split

### RelayMEM owns memory meaning and persistence

RelayMEM owns candidate meaning, memory kind, safety scope, persistence-policy interpretation, source lineage, memory-write idempotency, deterministic page construction, page/index/log semantics, recovery classification, and Primary-to-Secondary consolidation semantics.

Phase 6 consumes exact RelayMEM artifacts and must not redefine them.

### Phase 6 / RelayRUN owns deferred execution control

Phase 6 owns admission, finalized-response handoff, dispatch identity, durable queue records, enqueue, claim, lease, retry release, stale recovery, terminal state, worker invocation control, content-free status projection, and restart/checkpoint coordination.

### Protected source owner

The B2/B3 queue record is intentionally content-free. I1-B produces the exact claim-independent protected capture. C1-5 persists it separately before B2 queue publication and rehydrates it after restart. C1-0 binds a fresh source/scope to the exact current claim.

Missing, corrupt, or mismatched source evidence blocks execution. Queue metadata, trace, frontend history, and visible response text are never used to reconstruct protected content.

C1-5 restart completion applies only after durable source publication and enqueue. A process exit before the post-response background finalizer reaches those steps remains a separate I1 gap.

### RelaySLP never mutates SOUL directly

RelaySLP may read SOUL as a protected anchor and may later emit a separately governed proposal. It never writes or applies RelaySOUL directly.

## Implemented boundaries

### A1: deferred job admission

A1 validates trigger, processing stage, correlation, namespace, source lineage, response terminal state, and persistence policy. It performs no queue I/O or memory write.

### A2: response-finalization handoff

A2 consumes the exact A1 result for a finalized `turn_end` and creates a runtime-private enqueue candidate behind explicit gates. It performs no queue I/O or worker execution.

### B0: durable queue contract

B0 defines durable job schema, dispatch-idempotency ownership, state machine, revision/attempt/generation/lease invariants, retry/terminal semantics, restart/corruption behavior, and content-free projections.

### B1: dispatch/job-record preflight

B1 derives deterministic dispatch/job identities and one exact queued record candidate without queue I/O.

### C1-5 and B2 publication order

```text
exact finalized-turn protected capture
  -> durable protected-source create-if-absent
  -> unchanged B2 content-free durable enqueue
  -> optional process-local hot cache
```

An equivalent source artifact is idempotent. Same identity with different protected content is a collision and is never overwritten.

### B3: fenced queue lifecycle

B3 implements:

```text
claim
renew_lease
retry_release
stale_recovery
commit_terminal
```

It provides revision/state/job/dispatch CAS, active owner/generation/token fencing, stale recovery, terminal immutability, nonblocking queue locking, and content-free lifecycle projection. It does not execute RelayMEM or decide memory meaning.

### C1-0: exact protected source

C1-0 accepts one exact current claimed record and one exact protected capture, validates all correlation, creates a request-local one-shot scope, and emits a runtime-private `relaymem.slp_primary_worker_source.v0`.

### C1-1: RelayMEM composition

C1-1 fixes the exact order:

```text
M3a -> M3b -> M3c -> M3d -> M3e -> M3f -> M3g -> M3h
```

It remains queue-agnostic and preserves every direct-helper validator.

### C1-2: one already-claimed worker

C1-2 executes one exact active claim. It revalidates or renews the lease before source consumption, M3e, M3g, and the final B3 transition. It uses C1-1 and C1-3 rather than duplicating memory semantics.

C1-2 owns bounded retry timing for transient lock contention and verified reconciliation partial progress. Corruption, policy hold, manual confirmation, and recovery isolation are not automatically retried.

### C1-3: pure outcome classification

C1-3 maps exact M3e/M3g/M3h evidence to bounded B3 retry or terminal intent without queue, filesystem, clock, random, config, or memory I/O.

### C1-4: integrated fault smoke

C1-4 verifies normal success, stale claim fencing, lease loss at side-effect boundaries, M3g/M3h lock contention, M3e and reconciliation crash convergence, terminal-commit crash, idempotent new-claim convergence, corruption isolation, and content-free diagnostics.

### C1-5: durable protected source

C1-5 persists the claim-independent capture separately, validates identity and integrity, rehydrates after restart, retains it across retry/stale recovery, and removes it only after canonical terminal commit.

## Next integration boundary

The next slice is deliberately smaller than a scheduler:

```text
one exact queued canonical B3 record
  -> canonical B3 claim
  -> C1-5 protected capture lookup
  -> fresh C1-0 source and scope
  -> C1-2 one-claimed worker
  -> B3 retry release or terminal commit
```

It must not:

- scan the queue,
- run a daemon,
- create a generalized worker pool,
- sleep until retry time,
- own broad backoff policy,
- redefine M3 semantics,
- execute inline with visible response delivery.

## End-to-end recall validation

After the one-job adapter exists, prove:

```text
turn 1
  -> source publication and enqueue
  -> explicit B3 claim
  -> C1-5 rehydrate
  -> C1-2 forms Primary MEM
  -> B3 terminal success

turn 2
  -> RelayMEM retrieval
  -> RelayCTX injection
  -> backend response uses formed memory
```

The smoke must verify character/namespace scope, duplicate dispatch, retry behavior, both idempotency domains, source correlation, no public-content leakage, and no cross-character selection.

## Later Phase 6 work

After the Primary MEM loop is proven:

- add scheduler/service lifecycle only from concrete operational requirements,
- deepen RelayRUN checkpoint/retry-budget integration,
- add Secondary MEM jobs after RelayMEM-M4,
- add RelaySOUL proposal handoff without direct mutation,
- add explicit isolation/dead-letter policy only when bounded requirements exist.

## Idempotency separation

```text
Dispatch idempotency
  owned by Phase 6 / RelayRUN
  prevents duplicate logical queue dispatch

Memory-write idempotency
  owned by RelayMEM
  prevents duplicate durable memory application
```

A job retry may be valid while an existing memory write remains exact. Dispatch key, lease token, claim generation, and memory-write key must not be collapsed.

## Safety invariants

All Phase 6 slices preserve:

- visible response delivery never waits for SLP completion,
- SLP failure never invalidates an already valid response,
- default-off and dry-run-first rollout where applicable,
- fail-closed schema, namespace, policy, lineage, queue, lease, and source correlation,
- protected content remains outside queue and generic diagnostics,
- public projections remain content-free,
- safe ordinary MEM formation may be autonomous only when RelayMEM gates pass,
- sensitive, contradictory, destructive, cross-namespace, or SOUL-affecting changes remain held or blocked,
- RelaySLP never directly mutates SOUL,
- TTS/audio/avatar execution remains outside RelayLM Core.

## Active completion criterion

Phase 6-C1 is restart-complete for protected-source recovery of durably enqueued jobs. Phase 6 is product-complete for I1 only when ordinary queued work reaches C1-2 through the one-job adapter, queue state converges correctly, a later turn retrieves and uses the memory, and the separate pre-enqueue background-finalizer crash window is resolved or explicitly bounded.

<!-- phase6c2-status:start -->
## Phase 6-C2 completion alignment

The bounded E-to-F integration is complete for one caller-selected canonical queued job:

```text
I1-B producer: complete
B3 lifecycle: complete
C1-0 through C1-5: complete
C2 one-job claim/rehydrate/execute adapter: complete
next-turn recall and scope isolation: next
SOUL Lab real observation: later
auditable Correct operation: later
```

C2 delegates claim mutation to canonical B3, protected-source preparation to C1-5, and execution plus retry/terminal transition to the unchanged C1-2 worker. It does not add queue scanning, scheduling, polling, daemon/service lifecycle, a worker pool, pre-enqueue background-finalizer crash recovery, next-turn recall, memory correction, or Secondary MEM.

See [Phase 6-C2 One Queued Primary Worker Integration](phase6c2_one_queued_primary_worker_integration.md).
<!-- phase6c2-status:end -->
