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
relaylm_not_authoritative_for:
  - queue scanning, scheduling, daemon, or generalized worker pools
  - protected durable source artifact schema
  - RelayMEM page, index, or log semantics owned by M3a-M3h
  - Secondary MEM, RelaySOUL mutation, or SOUL Lab runtime behavior
relaylm_related_authority:
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
---
# Phase 6-C1-2 One-Claimed Primary MEM Worker Handoff

## Status

Phase 6-C1-2 is implemented as a production helper for exactly one already-claimed canonical B3 job:

```python
execute_relaymem_slp_primary_worker(request)
```

The worker accepts one exact claimed record, one exact unconsumed C1-0 source, its exact one-shot scope, the queue root, and the RelayMEM store root.

It does not scan or select queued work, reconstruct protected content from queue metadata, or execute inline with visible response delivery.

## Source ownership

I1-B produces the claim-independent protected capture. C1-5 persists it separately before B2 queue publication. The process-local registry remains an optional hot cache.

The preparation adapter:

```python
prepare_relaymem_slp_primary_worker_source_for_claim(...)
```

resolves the protected capture from the hot cache or durable C1-5 store, validates the exact current claim, creates a fresh C1-0 request scope, and builds a fresh unconsumed C1-0 source.

The worker owns one-shot source consumption at `before_source_consumption`.

Ownership rules:

- terminal success or terminal failure: close the prepared scope, release hot-cache state, and run C1-5 post-terminal cleanup,
- retry release: close only the prepared scope and retain the durable capture,
- lease loss or technical block: do not silently discard the durable capture,
- process restart: rehydrate the claim-independent capture and create a fresh source/scope for the new claim,
- stale or consumed source objects remain invalid even when the durable capture is still valid.

The legacy registry `consume_for_claim()` API remains for compatibility. C1-2 integration uses retry-safe preparation rather than passing a previously consumed source.

## Governed candidate identity

The I1-B governed-experience artifact owns the turn-specific content-free `candidate_id`. The serialized compose facade supplies that exact identifier to M3a, and the exact M3a candidate flows unchanged through M3b and must match the governed artifact at M3c.

The worker does not derive candidate identity from queue metadata or collapse dispatch identity into memory-write identity.

## Runtime sequence

```text
exact request and claimed-record validation
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

## Technical failure versus policy meaning

M3a/M3b `blocked` becomes a terminal memory-policy outcome only when exact private evidence proves the policy meaning.

Helper exceptions, malformed stage results, schema drift, impossible shapes, or missing exact evidence are not reclassified as policy failure. They remain safely blocked without false success or stale queue commit.

## Retry policy

C1-2 calculates retry timing internally. A caller-supplied non-null `retry_not_before` is rejected.

- transient lock contention: bounded short backoff with deterministic jitter,
- verified reconciliation partial progress: bounded longer backoff with deterministic jitter,
- maximum worker attempts: finite,
- attempt exhaustion: terminal failed with bounded reason,
- retry timestamps are later than the queue update timestamp,
- corruption, policy hold, manual confirmation, and recovery isolation are never automatically retried.

Jitter uses runtime-private identity, generation, and retry class. Exact identifiers and timestamps remain absent from public projection.

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

Only exact frozen worker/source types and complete canonical B3 records are accepted. Lookalikes, public projections, bool/int confusion, wrong schemas, impossible gates, stale claims, and cross-request source reuse fail closed.

## Lease and crash behavior

M3e and M3g checkpoints use canonical B3 `renew_lease`. Successful renewal increments revision and replaces the worker's expected record.

- lease loss before source consumption leaves the prepared source unconsumed,
- lease loss before M3e prevents page publication,
- lease loss before M3g preserves an already-published page but prevents index/log mutation,
- lease loss before final transition prevents stale retry/terminal commit.

Completed durable side effects are not rolled back. A later claim builds a fresh source from the retained durable capture and converges through M3e/M3g idempotency and M3h classification.

## Public projection

The public projection and `PipelineNodeResult` expose bounded statuses, checkpoint booleans, renewal count, pipeline status, outcome transition kind, retryable/terminal flags, queue-transition-performed, and bounded reason IDs.

They omit source messages, governed content, page/index/log content, roots and filenames, namespace and runtime identifiers, lineage and idempotency keys, claim material, timestamps, exception text, and private nested results.

## Validation

```bash
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_review_fix_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_worker_integration_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_durable_protected_source_smoke.py
```

## Remaining boundary

C1-5 now provides restart-complete protected-source recovery for durably enqueued jobs.

C1-2 still does not implement a queue scanner, automatic claim scheduler, daemon supervision, generalized worker pool, the thin one-job queued-record claim/rehydrate adapter, later-turn recall proof, or SOUL Lab observation. Those remain subsequent I1 integration work.

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
