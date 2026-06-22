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
  - phase6c1_primary_mem_worker_contract.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_execution_design.md
  - relaymem_slp_current_target.md
  - memory_lifecycle_design.md
  - relayrun_runtime_checkpoint_design.md
  - ../PROJECT_STATUS.md
---
# Phase 6 Asynchronous RelaySLP Bounded Slice

## Status

Phase 6 is implemented through fenced durable queue lifecycle helpers. The exact Phase 6-C1 worker contract is now defined; worker code is pending.

```text
Phase 6-A0 ownership and sequencing: complete
Phase 6-A1 deferred job-admission preflight: complete as helper-only
Phase 6-A2 response-finalization handoff: complete as helper-only
Phase 6-B0 durable queue contract: complete
Phase 6-B1 dispatch/job-record preflight: complete as helper-only
Phase 6-B2 atomic durable enqueue: complete as direct helper
Phase 6-B3 claim/renew/retry/stale/terminal lifecycle: complete as direct helper
request-runtime enqueue wiring: pending
Phase 6-C1 worker contract: defined
Phase 6-C1 worker implementation: next
```

A1, A2, B1, B2, and B3 are exact bounded components but are not automatically invoked as one ordinary request-runtime path. B2 can durably create or classify a queued record. B3 can safely claim and transition it. No current scheduler or worker executes RelayMEM processing.

The B2/B3 queue record is intentionally content-free. The C1 contract therefore requires a separately protected exact worker-source bundle; queue metadata alone cannot recreate the governed title, summary, messages, or source artifacts required by M3a/M3c.

## Purpose

RelaySLP is the deferred memory compiler. It improves future memory after the normal response path and must not delay or invalidate an already valid visible response.

Phase 6 owns asynchronous orchestration around RelaySLP without duplicating RelayMEM memory semantics or persistence rules.

```text
completed finalized turn
  -> A1 admission
  -> A2 response handoff
  -> B1 dispatch and durable-record candidate
  -> B2 durable enqueue
  -> B3 claim/lease/retry/stale/terminal lifecycle
  -> Phase 6-C1 worker invokes RelayMEM-owned processing
  -> future turns can retrieve formed memory
```

## Ownership split

### RelayMEM owns memory meaning and persistence primitives

RelayMEM owns:

- Primary MEM candidate classification,
- memory kind and safety scope,
- RelaySCN persistence-policy interpretation,
- RelayEMO salience metadata interpretation,
- source lineage and memory-write preflight,
- memory-write idempotency,
- deterministic Primary page construction,
- page/index/log apply semantics,
- Primary-to-Secondary consolidation semantics.

Phase 6 consumes exact RelayMEM artifacts and must not redefine them.

### Phase 6 / RelayRUN owns deferred execution control

Phase 6 owns:

- deferred job admission,
- finalized-response handoff,
- dispatch identity and duplicate-dispatch prevention,
- durable queue records,
- enqueue, claim, lease, retry-release, stale recovery, and terminal state,
- worker invocation control,
- content-free job status projections,
- later checkpoint/restart integration,
- independence of visible response delivery from SLP work.

### Protected source owner

Request-runtime integration must preserve an exact content-bearing source bundle outside the content-free queue and generic trace. That owner supplies governed messages, scene/affect artifacts, lineage correlation, and the governed-experience artifact required by C1.

The first live-process slice may retain that bundle in process. Restart-complete I1 behavior requires a protected durable source artifact or another exact rehydratable owner. Missing source evidence must block execution rather than trigger reconstruction from queue metadata, traces, or frontend history.

### RelaySLP never directly mutates SOUL

RelaySLP may later produce a separately governed RelaySOUL proposal candidate. It must never write or apply RelaySOUL directly.

## Implemented boundaries

### Phase 6-A1: deferred job admission

A1 validates bounded trigger, processing stage, correlation, namespace, source lineage, response terminal state, and persistence-policy status. It performs no queue I/O, worker invocation, memory write, or SOUL mutation.

### Phase 6-A2: response-finalization handoff

A2 consumes the exact A1 private result and matching public projection for a finalized `turn_end`. It may create one runtime-private metadata-only enqueue candidate behind explicit gates. It performs no queue I/O, dispatch-key allocation, worker invocation, memory write, SOUL mutation, or visible-response mutation.

### Phase 6-B0: durable queue contract

B0 defines the durable job schema, dispatch-idempotency ownership, state machine, revision/attempt/generation/lease invariants, retry and terminal semantics, restart/corruption behavior, content-free projection, and visible-response independence.

### Phase 6-B1: dispatch/job-record preflight

B1 consumes exact A2 runtime-private artifacts, derives deterministic dispatch and job identities, initializes one exact queued durable-record candidate, and emits a content-free projection. It performs no queue I/O or worker execution.

### Phase 6-B2: atomic durable enqueue

B2 consumes the exact B1 result and candidate, assigns durable timestamps for new records, and atomically publishes one canonical queued record through no-clobber create-if-absent semantics.

B2 classifies:

```text
enqueued_new
duplicate_existing
blocked_collision
blocked_corrupt
write_failed
```

B2 performs no claim, lease, retry transition, worker invocation, memory write, SOUL mutation, request-runtime wiring, or visible-response mutation.

### Phase 6-B3: fenced durable queue lifecycle

B3 consumes an exact runtime-private transition request and revalidates the complete canonical B2 record. It implements:

```text
claim
renew_lease
retry_release
stale_recovery
commit_terminal
```

B3 provides:

- revision, state, job, and dispatch identity compare-and-swap,
- active owner, claim-generation, and lease-token fencing,
- owner-independent stale recovery with generation/token fencing,
- bounded retry/failure classification storage without policy decisions,
- queued cancellation and claimed success/failure/cancellation,
- absolute terminal immutability,
- nonblocking shared/exclusive queue-root locking,
- inode-and-byte CAS and durable atomic replacement,
- content-free lifecycle projection.

B3 does not generate `dead_letter`; that state remains reserved for a later explicit isolation policy. It does not execute RelaySLP or RelayMEM, decide candidate meaning, reuse memory-write identity, mutate RelaySOUL, wire request runtime, or make visible-response success depend on queue state.

B3 is the final queue-only prerequisite for the active integration milestone. Do not extend the B series with unrelated helper-only work unless a concrete queue safety defect requires it.

## Next boundary: Phase 6-C1 worker implementation

[Phase 6-C1 Primary MEM Worker Contract](phase6c1_primary_mem_worker_contract.md) defines the exact integration boundary.

The first worker executes one already-claimed job only under the exact active B3 lease fence. It requires:

1. one exact canonical claimed record,
2. one exact protected `relaymem.slp_primary_worker_source.v0` bundle correlated to that record,
3. a configured RelayMEM store root,
4. a RelayMEM-owned M3a-M3h compose boundary,
5. bounded outcome mapping to B3 retry release or terminal commit.

```text
B3 active lease
  + protected worker source
  -> M3a -> M3b -> M3c -> M3d -> M3e -> M3f -> M3g -> M3h
  -> B3 retry_release or commit_terminal
```

The worker must renew or revalidate its lease before source consumption, M3e, M3g, and queue commit. It stops before a new side effect after lease loss.

The worker maps M3g/M3h lock contention to bounded retry, verified partial reconciliation to retry release, policy outcomes to failed classifications, manual-confirmation and journal candidates to terminal isolation classifications, and success only to M3h-verified durable state.

Dispatch idempotency remains Phase 6-owned. Memory-write idempotency remains RelayMEM-owned. A new claim after a crash reruns the deterministic RelayMEM chain from the exact protected source; it does not serialize M3f plans or memory content into the queue record.

Phase 6-C1 must not initially become a generalized scheduler, broad worker pool, or unrestricted retry-policy engine. One bounded execution path is sufficient for the first end-to-end proof.

## Parallel required integration: request-runtime enqueue and protected source wiring

Finalized ordinary managed turns still need A1 -> A2 -> B1 -> B2 wiring and protected source retention.

Required behavior:

- finalize and emit the visible response independently,
- construct only exact runtime-private handoff artifacts,
- enqueue after response-finalization eligibility is known,
- retain exact protected source evidence outside the queue and generic trace,
- correlate source evidence with job/dispatch/run/turn/session/namespace/lineage identity,
- record content-free status when disabled, skipped, held, blocked, enqueued, duplicated, or failed,
- preserve default-off and dry-run-first rollout,
- never copy source content into generic trace, public errors, or queue projections,
- never execute the worker inline with visible response delivery.

## End-to-end recall validation

After runtime enqueue, protected source wiring, and Phase 6-C1 worker execution exist, prove:

```text
turn 1
  -> enqueue and protected source retention
  -> B3 claim
  -> Phase 6-C1 worker forms Primary MEM
  -> B3 terminal success

turn 2
  -> RelayMEM retrieval
  -> RelayCTX injection
  -> backend response uses the formed memory
```

The smoke must verify character scope, namespace scope, duplicate-dispatch handling, stale/retry behavior, restart behavior, both idempotency domains, source-bundle correlation, M3g/M3h lock contention, lease loss around side effects, and absence of content leakage into public diagnostics.

## Later Phase 6 work

After the Primary MEM runtime loop is proven:

- integrate RelayRUN checkpoint/restart and retry-budget policy more deeply,
- add broader persistence/recovery coordination only where M3h evidence justifies it,
- support Secondary MEM consolidation jobs after RelayMEM-M4 exists,
- add RelaySOUL proposal handoff without direct mutation,
- add explicit dead-letter/manual-confirmation policy only when bounded requirements exist.

These later stages must not block the initial Primary MEM end-to-end loop.

## Idempotency separation

Dispatch idempotency and memory-write idempotency remain distinct:

```text
Dispatch idempotency
  prevents duplicate queue scheduling or execution
  owned by Phase 6 / RelayRUN

Memory-write idempotency
  prevents duplicate durable memory application
  owned by RelayMEM
```

A job may be retried while an already-completed memory write remains deduplicated. The dispatch key, lease token, claim generation, and memory-write key must not be collapsed.

## Safety invariants

All Phase 6 slices must preserve:

- normal response and stream delivery do not wait for SLP completion,
- SLP failure does not invalidate an already valid visible response,
- default-off and dry-run-first rollout where applicable,
- fail-closed schema, namespace, policy, lineage, queue, lease, and source-correlation handling,
- content-bearing material remains in protected memory/SLP domains,
- public diagnostics remain content-free,
- ordinary safe MEM formation may be autonomous only when RelayMEM gates pass,
- sensitive, contradictory, destructive, cross-namespace, or SOUL-affecting changes remain held or blocked,
- RelaySLP never directly mutates SOUL,
- TTS/audio/avatar execution remains outside RelayLM Core.

## Active completion criterion

Phase 6 is not product-complete when B3 lands or when the C1 contract is written. For the current milestone, Phase 6 is complete enough only when an ordinary finalized turn can enqueue work and retain protected source evidence, a Phase 6-C1 worker can execute the existing Primary MEM path under an exact active B3 lease, queue state reaches a correct terminal or retry outcome, restart can rehydrate exact source evidence, and a later turn can retrieve the formed memory.
