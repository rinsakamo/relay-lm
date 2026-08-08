---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_one_claimed_primary_worker
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - one-claimed Primary MEM worker request, result, projection, or lease checkpoint semantics change
  - protected source persistence or scheduler ownership changes
  - retry bounds or source-retention ownership changes
  - RT-1 Primary writer decision carriage changes
  - RT-1D-R5 or R6 retires the Primary worker path
relaylm_not_authoritative_for:
  - queue scanning, scheduling, daemon, or generalized worker pools
  - protected durable source artifact schema
  - RelayMEM page, index, or log semantics owned by M3a-M3h
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - Secondary MEM, RelaySOUL mutation, or SOUL Lab runtime behavior
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - relaymem_slp_current_target.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../PROJECT_STATUS.md
---
# Phase 6-C1-2 One-Claimed Primary MEM Worker Handoff

Last reviewed: 2026-08-08 JST

## Status

Phase 6-C1-2 remains implemented as a production helper for exactly one already-claimed canonical B3 Primary job:

```python
execute_relaymem_slp_primary_worker(request)
```

The worker accepts one exact claimed record, one exact unconsumed C1-0 source, its exact one-shot scope, the queue root, the RelayMEM store root, and the caller-carried exact RT-1 Primary writer decision.

It does not scan or select queued work, reconstruct protected content from queue metadata, execute inline with visible response delivery, or mint/reconstruct writer authority.

Under RT-1D-R4, C1-2 is a retained Primary compatibility writer surface. Its lease/source/M3 machinery may execute only after the exact worker request has passed the independent Primary writer-decision gate described below. R5/R6 own final retirement/disposition.

## Primary writer gate

`RelayMEMSLPPrimaryWorkerRequest` now carries one immutable `SubjectiveMemRetrievalPrimaryWriterDecision`. The cutover domain owns the decision class; C1-2 only validates and consumes it.

The worker entry order is intentionally fail closed:

```text
exact worker request validation
  -> exact carried Primary writer decision must permit write
       -> otherwise invalid_input / primary_writer_decision_rejected
       -> no B3 active-claim validation
       -> no source correlation or consumption
       -> no M3 pipeline execution
  -> enabled / dry-run / apply behavior
  -> initial active B3 lease fence
  -> source validation and pipeline execution
```

The focused worker smoke proves this separation by replacing the carried decision with a foreign object and patching `_check_active_claim`: the request is rejected as `invalid_input` and the claim check is never called.

A valid claimed record, active lease, prepared source, prior retry, existing Primary page, or historical worker completion is not writer permission. C1-2 does not infer permission from those states, and it does not convert a rejected decision into retry, hold, policy block, dry-run, or fallback behavior.

The exact decision is caller-carried. C1-2 does not re-resolve the durable RT-1 cutover chain during lease checkpoints. The M3 pipeline independently validates the same carried decision before protected-source consumption, providing a second fail-closed boundary without turning lease renewal into a writer-state re-read.

## Source ownership

I1-B produces the claim-independent protected capture. C1-5 persists it separately before B2 queue publication. The process-local registry remains an optional hot cache.

The preparation adapter:

```python
prepare_relaymem_slp_primary_worker_source_for_claim(...)
```

resolves the protected capture from the hot cache or durable C1-5 store, validates the exact current claim, creates a fresh C1-0 request scope, and builds a fresh unconsumed C1-0 source.

The worker owns one-shot source consumption at `before_source_consumption`, but only after the exact request and Primary writer decision have passed their entry gates.

Ownership rules:

- terminal success or terminal failure: close the prepared scope, release hot-cache state, and run C1-5 post-terminal cleanup,
- retry release: close only the prepared scope and retain the durable capture,
- lease loss or technical block: do not silently discard the durable capture,
- process restart: rehydrate the claim-independent capture and create a fresh source/scope for the new claim,
- stale or consumed source objects remain invalid even when the durable capture is still valid.

The legacy registry `consume_for_claim()` API remains for compatibility. C1-2 integration uses retry-safe preparation rather than passing a previously consumed source.

Source persistence and retryability preserve work/evidence, not writer authorization. A later invocation must still carry an exact decision accepted by the worker entry gate.

## Governed candidate identity

The I1-B governed-experience artifact owns the turn-specific content-free `candidate_id`. The serialized compose facade supplies that exact identifier to M3a, and the exact M3a candidate flows unchanged through M3b and must match the governed artifact at M3c.

The worker does not derive candidate identity from queue metadata or collapse dispatch identity into memory-write identity. Candidate identity also does not grant Primary writer permission.

## Runtime sequence

```text
exact request validation
  -> exact Primary writer-decision gate
  -> initial active B3 lease fence
  -> exact C1-0 source correlation validation
  -> checkpoint before source consumption
  -> M3a-M3d
  -> renew and fence before M3e
  -> M3e page publication
  -> M3f
  -> renew and fence before M3g
  -> M3g index-before-log reconciliation
  -> M3h recovery audit
  -> C1-3 pure outcome classification
  -> bounded retry policy or terminal intent
  -> final active B3 lease fence
  -> canonical B3 retry_release or commit_terminal
```

RelayMEM compose remains queue-agnostic. The worker owns canonical queue reread, owner/generation/token/revision/expiry fencing, lease renewal, and replacement of the expected record after renewal.

The three worker checkpoints remain B3 claim/lease fences. They do not independently reconstruct or refresh the RT-1 writer decision. The immutable caller-carried decision is instead checked at C1-2 entry and again by the M3 pipeline boundary.

## Technical failure versus policy meaning

M3a/M3b `blocked` becomes a terminal memory-policy outcome only when exact private evidence proves the policy meaning.

Helper exceptions, malformed stage results, schema drift, impossible shapes, or missing exact evidence are not reclassified as policy failure. They remain safely blocked without false success or stale queue commit.

`primary_writer_decision_rejected` is an authorization/input failure before those pipeline policy classifications. It is not reclassified as a memory-policy outcome.

## Retry policy

C1-2 calculates retry timing internally. A caller-supplied non-null `retry_not_before` is rejected.

- transient lock contention: bounded short backoff with deterministic jitter,
- verified reconciliation partial progress: bounded longer backoff with deterministic jitter,
- maximum worker attempts: finite,
- attempt exhaustion: terminal failed with bounded reason,
- retry timestamps are later than the queue update timestamp,
- corruption, policy hold, manual confirmation, and recovery isolation are never automatically retried.

Jitter uses runtime-private identity, generation, and retry class. Exact identifiers and timestamps remain absent from public projection.

A retryable queue outcome means the work may be attempted again under B3 rules. It does not preserve or synthesize RT-1 writer authorization for that later invocation.

## Exact boundaries

Production modules:

```text
relaylm/relaymem_slp_primary_worker.py
relaylm/relaymem_slp_primary_worker_source_adapter.py
```

Schemas:

```text
relaymem.slp_primary_worker_request.v0
relaymem.slp_primary_worker_result.v0
relaymem.slp_primary_worker_projection.v0
relaymem.slp_primary_worker_prepared_source_projection.v0
```

The exact request includes the Primary writer decision in addition to the previously documented claimed-record/source/scope/roots/gates. Only exact frozen worker/source types and complete canonical B3 records are accepted. Lookalikes, public projections, bool/int confusion, wrong schemas, impossible gates, stale claims, cross-request source reuse, and non-permitted writer decisions fail closed.

## Lease and crash behavior

M3e and M3g checkpoints use canonical B3 `renew_lease`. Successful renewal increments revision and replaces the worker's expected record.

- lease loss before source consumption leaves the prepared source unconsumed,
- lease loss before M3e prevents page publication,
- lease loss before M3g preserves an already-published page but prevents index/log mutation,
- lease loss before final transition prevents stale retry/terminal commit.

Completed durable side effects are not rolled back. A later claim builds a fresh source from the retained durable capture and converges through M3e/M3g idempotency and M3h classification, subject to the exact writer decision carried by that later worker invocation.

Lease/crash recovery is not an alternate RT-1 authorization channel and cannot turn `rejected` into `permitted`.

## Public projection

The public projection and `PipelineNodeResult` expose bounded statuses, checkpoint booleans, renewal count, pipeline status, outcome transition kind, retryable/terminal flags, queue-transition-performed, and bounded reason IDs.

They omit source messages, governed content, page/index/log content, roots and filenames, namespace and runtime identifiers, lineage and idempotency keys, claim material, timestamps, exception text, private writer-decision identity, and private nested results.

## Validation

```bash
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_review_fix_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_worker_integration_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_durable_protected_source_smoke.py
```

The focused review-fix smoke includes explicit writer-decision rejection before `_check_active_claim`. The repository workflow/test registry remains command authority; this list records the handoff's regression boundary.

## Remaining boundary

C1-5 provides restart-complete protected-source recovery for durably enqueued jobs, and C2 owns the thin one-job queued-record claim/rehydrate adapter above C1-2. Those completed capabilities do not grant writer permission.

C1-2 does not own queue scanning/scheduling, daemon supervision, generalized worker pools, ordinary reader authority, or RT-1 cutover/retirement state. Repository-wide status for historically separate scheduling, recall, observation, correction, and Secondary MEM slices is owned by Project Status and their own authorities rather than this handoff.

## RT-1D-R5 / R6 boundary

Current Project Status records R4 activation/P8 complete and R5 immediate retirement unstarted. C1-2 therefore remains a live retained Primary compatibility worker, but its execution is subordinate to the exact writer decision.

R5/R6 own final retirement or explicitly retained read-only disposition of Primary worker surfaces after exact dependency characterization. This handoff does not authorize deleting runtime code, durable queue/source evidence, or worker tests ahead of the owning retirement transaction.

Retirement must not be simulated by weakening worker validation, bypassing the writer decision, treating rejected authorization as retryable policy state, or moving Primary mutation semantics into another owner.
