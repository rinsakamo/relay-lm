---
relaylm_doc_type: implementation_plan
relaylm_authority: phase6_async_relayslp_bounded_slice
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6 RelaySLP slice lands
  - deferred job admission or orchestration semantics change
  - RelayMEM-M3 or M4 producer consumer boundary changes
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
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_execution_design.md
  - relaymem_slp_current_target.md
  - memory_lifecycle_design.md
  - relayrun_runtime_checkpoint_design.md
  - ../PROJECT_STATUS.md
---
# Phase 6 Asynchronous RelaySLP Bounded Slice

## Status

Phase 6 is implemented through the helper-only A2 boundary:

```text
Phase 6-A0 documentation and ownership boundary: complete
Phase 6-A1 deferred RelaySLP job-admission preflight: complete
Phase 6-A2 response-finalization handoff and dry-run enqueue candidate: complete
```

The next implementation boundary is Phase 6-B: a separately designed bounded durable queue with dispatch idempotency and enqueue/claim/lease/terminal-state semantics.

A1 and A2 remain helper-only, default-off, dry-run-first, fail-closed, and free of request-runtime wiring, queue I/O, worker execution, memory persistence, and RelaySOUL mutation.

## Purpose

RelaySLP is the deferred memory compiler. It improves future memory after the normal response path and must not delay or invalidate an already valid visible response.

Phase 6 introduces asynchronous orchestration around RelaySLP without duplicating RelayMEM-M memory semantics or persistence preflight.

```text
completed finalized turn event
  -> A1 deferred job-admission preflight
  -> admitted / held / blocked / skipped
  -> A2 response-finalization handoff
  -> runtime-private dry-run enqueue candidate
  -> later Phase 6-B queue and dispatch boundary
  -> later worker and RelayMEM-owned processing
```

## Ownership split

### RelayMEM-M owns memory semantics

The independent RelayMEM-M track owns:

- Primary MEM candidate classification,
- memory kind and safety scope,
- RelaySCN persistence-policy interpretation,
- RelayEMO salience metadata interpretation,
- Primary MEM source lineage and write preflight,
- memory-write idempotency,
- Primary-to-Secondary MEM consolidation semantics,
- durable page, index, and log formats and apply primitives.

Phase 6 consumes those bounded artifacts. It must not redefine them.

### Phase 6 owns deferred execution orchestration

Phase 6 owns:

- deferred job admission,
- trigger and processing-stage classification,
- run, turn, session, and namespace correlation,
- response-finalization handoff,
- dispatch idempotency in Phase 6-B,
- enqueue, claim, lease, retry, and terminal-state orchestration in later slices,
- content-free job status projections,
- RelayRUN checkpoint and retry integration in later slices,
- ensuring visible response delivery remains independent from SLP execution.

### RelayRUN owns control state, not memory meaning

RelayRUN may own job correlation, node state, checkpoint state, retry eligibility, and duplicate-dispatch prevention. It must not decide memory meaning, candidate safety scope, page content, consolidation meaning, or SOUL mutation eligibility.

### RelaySLP does not mutate SOUL

RelaySLP may produce a RelaySOUL proposal candidate through a separately governed path. It must never write RelaySOUL files or directly apply identity, values, output-policy, or relationship-anchor changes.

## Relationship to RelayMEM-M3b

RelayMEM-M3b owns content-free source-lineage validation, bounded target classification, autonomous-apply eligibility, memory-write preflight, and memory-write idempotency.

Phase 6-A1 consumes M3b lineage artifacts. Phase 6-A2 consumes the exact A1 private result and its matching content-free projection. Neither A1 nor A2 creates or uses a memory-write idempotency key.

The two idempotency layers remain distinct:

```text
Dispatch idempotency
  prevents the same deferred job from being durably enqueued or claimed twice
  owned by Phase 6-B orchestration / RelayRUN control state

Memory-write idempotency
  prevents the same candidate or page update from being durably applied twice
  owned by RelayMEM write preflight and persistence apply
```

A job may be retried while a previously completed memory write remains deduplicated. The keys must never be collapsed into one artifact.

## Phase 6-A1: deferred job-admission preflight — complete

A1 is implemented in `relaylm/relaymem_slp_job_admission.py` through:

```text
build_relaymem_slp_job_admission_preflight(...)
```

Implemented schemas:

```text
relaymem.slp_job_admission_preflight.v0
relaymem.slp_job_admission_projection.v0
```

Initially supported trigger modes:

```text
turn_end
explicit_memory_request
```

Initially supported processing stages:

```text
primary_formation
primary_write_preflight
```

Implemented outcomes:

```text
skipped
blocked
held
admitted_dry_run
eligible_for_enqueue
```

`eligible_for_enqueue` is structural eligibility only. A1 performs no queue I/O and creates no durable job.

A1 validates fixed bounded metadata, the M3b-compatible source-lineage schema and identity shape, strict booleans, namespace, source count, terminal response state, and persistence-policy status. Its public projection omits runtime-private references, lineage fingerprints, candidate arrays, and both idempotency-key domains.

See [Phase 6-A1 RelaySLP Job Admission Contract](phase6a1_relayslp_job_admission_contract.md).

## Phase 6-A2: response-finalization handoff — complete

A2 is implemented in `relaylm/relaymem_slp_response_handoff.py` through:

```text
build_relaymem_slp_response_finalization_handoff(...)
build_relaymem_slp_response_handoff_node_result(...)
```

Implemented schemas:

```text
relaymem.slp_response_handoff.v0
relaymem.slp_enqueue_candidate.v0
relaymem.slp_response_handoff_projection.v0
```

The initial A2 boundary accepts only finalized `turn_end` A1 results for `primary_formation` or `primary_write_preflight`. `explicit_memory_request` remains outside response-finalization handoff.

A2 validates:

- the exact A1 private-result schema,
- the exact A1 public-projection schema,
- strict booleans and fixed correlation keys,
- private-result/projection equality for shared fields,
- absence of prior queue, worker, memory, SOUL, or visible-response side effects,
- absence of dispatch and memory-write idempotency keys,
- finalized response, correlation, namespace, count, lineage fingerprint, runtime terminal state, and persistence-policy gates.

A2 may create one runtime-private metadata-only candidate when explicitly enabled and dry-run-only. It performs no queue I/O, enqueue, dispatch-key allocation, worker invocation, RelaySLP invocation, memory write, RelaySOUL mutation, or visible-response mutation.

The public `relaymem_slp_response_handoff` node result omits the candidate, identifiers, namespace value, lineage fingerprint, and both idempotency-key domains.

See [Phase 6-A2 RelaySLP Response-Finalization Handoff Contract](phase6a2_relayslp_response_handoff_contract.md).

## Phase 6-A non-goals

A1 and A2 do not implement:

- request-runtime wiring,
- a background thread, process, scheduler, or worker,
- filesystem or database job queues,
- durable enqueue delivery,
- dispatch idempotency,
- claim or lease state,
- Primary MEM candidate generation,
- Primary MEM write apply,
- Primary or Secondary MEM writes,
- Secondary MEM consolidation runtime,
- page, index, or log updates,
- generic RelayRUN resume or retry apply,
- RelaySOUL proposal generation or mutation,
- SOUL Lab memory APIs,
- TTS, audio, transport delivery, Live2D, avatar, or lip-sync behavior.

## Later bounded sequence

```text
Phase 6-B
  bounded durable queue
  dispatch idempotency
  enqueue / claim / lease / terminal states

Phase 6-C
  worker execution
  invokes RelayMEM-owned Primary formation, write preflight, or Secondary consolidation artifacts

Phase 6-D
  gated page/index/log persistence apply
  memory-write idempotency
  partial-failure and reconciliation handling

Phase 6-E
  RelayRUN checkpoint, retry budget, restart recovery, and terminal-failure integration
```

Each later slice requires its own explicit bounded design and smoke coverage. This document does not claim those stages are implemented.

## Phase 6-B entry conditions

Before durable queue work begins, Phase 6-B must define:

- a bounded durable job-record schema,
- how the A2 candidate is consumed without trusting public diagnostics as private source,
- dispatch-idempotency key ownership and derivation inputs,
- enqueue atomicity and duplicate handling,
- claim and lease state transitions,
- terminal success/failure/cancelled states,
- retry-class boundaries without memory semantic decisions,
- content-free public status projection,
- corruption, stale lease, and restart behavior,
- proof that queue work cannot delay or invalidate an already finalized response.

Phase 6-B must not use the M3b memory-write idempotency key as its dispatch key.

## Safety invariants

All Phase 6 slices must preserve:

- normal response and stream delivery do not wait for persistence I/O,
- SLP failure does not invalidate an already valid visible response,
- default-off and dry-run-first gates,
- fail-closed schema, namespace, policy, and lineage handling,
- content-bearing material remains inside protected memory/SLP domains,
- default trace, audit, public errors, and node-result projections remain content-free,
- ordinary safe MEM formation may be autonomous when RelayMEM gates pass,
- review-required, approval-required, destructive, contradictory, sensitive, or cross-namespace operations remain held or blocked,
- RelaySLP never directly mutates SOUL,
- Phase 5.5 stream/TTS behavior remains unchanged,
- TTS, audio, adapter delivery, Live2D/avatar, and lip-sync execution remain SOUL Lab Runtime MVP responsibilities.

## Implemented smoke coverage

A1 smoke coverage includes disabled/default behavior, dry-run admission, enqueue eligibility without enqueue, trigger/stage validation, correlation and namespace validation, lineage identity and schema validation, bounded metadata, strict booleans, terminal-state and policy handling, and content-free projection checks.

A2 smoke coverage includes disabled/default behavior, strict gates, dry-run candidate generation from both accepted A1 statuses, finalized-response enforcement, explicit-memory-request rejection, held/blocked/skipped propagation, exact private-result and public-projection validation, side-effect rejection, candidate omission from node diagnostics, and proof that queue, worker, memory, SOUL, and visible-response side effects remain false.
