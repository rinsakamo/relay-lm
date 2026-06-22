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
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_execution_design.md
  - relaymem_slp_current_target.md
  - memory_lifecycle_design.md
  - relayrun_runtime_checkpoint_design.md
  - ../PROJECT_STATUS.md
---
# Phase 6 Asynchronous RelaySLP Bounded Slice

## Status

Phase 6 is implemented through atomic durable enqueue:

```text
Phase 6-A0 ownership and sequencing: complete
Phase 6-A1 deferred job-admission preflight: complete as helper-only
Phase 6-A2 response-finalization handoff: complete as helper-only
Phase 6-B0 durable queue contract: complete
Phase 6-B1 dispatch/job-record preflight: complete as helper-only
Phase 6-B2 atomic durable enqueue: complete as direct helper
Phase 6-B3 claim/lease/retry/terminal lifecycle: next
request-runtime enqueue wiring: pending
worker execution: pending
```

A1, A2, B1, and B2 are exact bounded components but are not automatically invoked by ordinary request finalization. B2 can durably create or classify a queued record behind explicit gates, but no current scheduler or worker claims it.

## Purpose

RelaySLP is the deferred memory compiler. It improves future memory after the normal response path and must not delay or invalidate an already valid visible response.

Phase 6 owns asynchronous orchestration around RelaySLP without duplicating RelayMEM memory semantics or persistence rules.

```text
completed finalized turn
  -> A1 admission
  -> A2 response handoff
  -> B1 dispatch and durable-record candidate
  -> B2 durable enqueue
  -> B3 claim/lease/retry/terminal lifecycle
  -> worker invokes RelayMEM-owned processing
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

### RelaySLP never directly mutates SOUL

RelaySLP may later produce a separately governed RelaySOUL proposal candidate. It must never write or apply RelaySOUL directly.

## Implemented boundaries

### Phase 6-A1: deferred job admission

A1 validates bounded trigger, processing stage, correlation, namespace, source lineage, response terminal state, and persistence-policy status.

Supported initial trigger modes include `turn_end` and `explicit_memory_request`. Supported initial stages include `primary_formation` and `primary_write_preflight`.

A1 performs no queue I/O, worker invocation, memory write, or SOUL mutation.

### Phase 6-A2: response-finalization handoff

A2 consumes the exact A1 private result and matching public projection for a finalized `turn_end`. It may create one runtime-private metadata-only enqueue candidate behind explicit gates.

A2 performs no queue I/O, dispatch-key allocation, worker invocation, memory write, SOUL mutation, or visible-response mutation.

### Phase 6-B0: durable queue contract

B0 defines:

- the durable job schema,
- dispatch-idempotency ownership and derivation inputs,
- create-if-absent enqueue semantics,
- queued, claimed, succeeded, failed, cancelled, and dead-letter states,
- revision, attempt, claim-generation, lease-token, retry, and terminal invariants,
- stale-lease and restart behavior,
- corruption handling,
- content-free queue status projection,
- visible-response independence.

### Phase 6-B1: dispatch/job-record preflight

B1 consumes exact A2 runtime-private artifacts, derives deterministic dispatch and job identities, initializes one exact queued durable-record candidate, and emits a content-free projection.

B1 performs no queue I/O or worker execution.

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

## Next boundary: Phase 6-B3

B3 adds queue lifecycle transitions over exact B2 records:

- claim,
- lease issuance and renewal rules,
- claim-generation and lease-token fencing,
- retry release,
- stale-lease recovery,
- succeeded/failed/cancelled/dead-letter terminal transitions,
- content-free lifecycle projection.

B3 must not:

- execute RelaySLP or RelayMEM,
- decide candidate meaning or safety scope,
- reuse the memory-write idempotency key as the dispatch key,
- mutate RelaySOUL,
- make visible-response success depend on queue state.

B3 is the final queue-only prerequisite for the active integration milestone. Do not extend the B series with unrelated helper-only work unless a concrete queue safety defect requires it.

## Integration sequence after B3

### Phase 6-C0: request-runtime enqueue wiring

Wire finalized ordinary managed turns through A1, A2, B1, and B2.

Required behavior:

- finalize and emit the visible response independently,
- construct only exact runtime-private handoff artifacts,
- enqueue after response-finalization eligibility is known,
- record content-free status when disabled, skipped, held, blocked, enqueued, duplicated, or failed,
- preserve default-off and dry-run-first rollout,
- never copy source content into generic trace, public errors, or queue projections.

### Phase 6-C1: bounded Primary MEM worker

A worker claims one eligible job and invokes existing RelayMEM boundaries:

```text
M3a -> M3b -> M3c -> M3d -> M3e -> M3f -> M3g -> M3h
```

The worker owns stage execution and queue transitions only. RelayMEM continues to own memory meaning, write eligibility, page content, reconciliation, and recovery classification.

Worker outcomes must map to:

- terminal success when durable state is verified,
- retry release for bounded retryable operational failure,
- held or blocked terminal classification when RelayMEM policy forbids apply,
- dead-letter or manual-confirmation state only under explicit bounded rules.

### Phase 6-C2: end-to-end recall validation

Prove the ordinary loop:

```text
turn 1
  -> enqueue
  -> worker forms Primary MEM

turn 2
  -> RelayMEM retrieval
  -> RelayCTX injection
  -> backend response uses the formed memory
```

The smoke must verify character scope, namespace scope, duplicate-dispatch handling, restart behavior, and absence of content leakage into public diagnostics.

## Later Phase 6 work

After the Primary MEM runtime loop is proven:

- integrate RelayRUN checkpoint/restart and retry-budget policy more deeply,
- add broader persistence/recovery coordination only where M3h evidence justifies it,
- support Secondary MEM consolidation jobs after RelayMEM-M4 exists,
- add RelaySOUL proposal handoff without direct mutation.

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

A job may be retried while an already-completed memory write remains deduplicated. The keys and their schemas must not be collapsed.

## Safety invariants

All Phase 6 slices must preserve:

- normal response and stream delivery do not wait for SLP completion,
- SLP failure does not invalidate an already valid visible response,
- default-off and dry-run-first rollout where applicable,
- fail-closed schema, namespace, policy, and lineage handling,
- content-bearing material remains in protected memory/SLP domains,
- public diagnostics remain content-free,
- ordinary safe MEM formation may be autonomous when RelayMEM gates pass,
- sensitive, contradictory, destructive, cross-namespace, or SOUL-affecting changes remain held or blocked,
- RelaySLP never directly mutates SOUL,
- TTS/audio/avatar execution remains outside RelayLM Core.

## Active completion criterion

Phase 6 is not product-complete when B3 lands. For the current milestone, Phase 6 is complete enough only when an ordinary finalized turn can enqueue work, a worker can execute the existing Primary MEM path, queue state reaches a correct terminal or retry outcome, and a later turn can retrieve the formed memory.
