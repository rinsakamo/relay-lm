---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_one_claimed_primary_worker
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - one-claimed Primary MEM worker request, result, projection, or lease checkpoint semantics change
  - protected source persistence or scheduler ownership is implemented
  - retry bounds or source-retention ownership changes
relaylm_not_authoritative_for:
  - queue scanning, scheduling, daemon, or generalized worker pools
  - protected durable source persistence or restart rehydration
  - RelayMEM page, index, or log semantics owned by M3a-M3h
  - Secondary MEM, RelaySOUL mutation, or SOUL Lab runtime behavior
relaylm_related_authority:
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_primary_worker_outcome_classifier.md
---
# Phase 6-C1-2 One-Claimed Primary MEM Worker Handoff

## Status

Phase 6-C1-2 is implemented as a production helper for exactly one already-claimed canonical B3 job:

```python
execute_relaymem_slp_primary_worker(request)
```

The worker accepts one exact claimed record, one exact unconsumed C1-0 protected source, its request-local scope, the queue root, and the RelayMEM store root. It does not scan the queue, select jobs, reconstruct protected content from queue metadata, or execute inline with visible response delivery.

## I1-B source ownership

The I1-B registry retains the protected 16-field source capture across claims. The integration adapter:

```python
prepare_relaymem_slp_primary_worker_source_for_claim(...)
```

builds a fresh unconsumed C1-0 source and fresh request scope for the exact active claim while leaving the protected registry capture retained. The worker owns one-shot source consumption at its `before_source_consumption` checkpoint.

Ownership rules are:

- terminal success or terminal failure: close the prepared scope and release the retained registry capture;
- retry release: close only the prepared scope and retain the protected capture for the next claim;
- lease loss or technical block: do not silently discard the retained capture;
- process restart: still not restart-complete because the registry remains process-local.

The legacy registry `consume_for_claim()` API remains unchanged for compatibility. C1-2 integration uses the retry-safe preparation adapter instead of passing an already-consumed source to the worker.

## Runtime sequence

```text
exact request and claimed-record validation
  -> initial active B3 lease fence
  -> exact C1-0 source correlation validation
  -> compose checkpoint before source consumption
  -> M3a-M3d
  -> renew and fence immediately before M3e
  -> M3e page publication
  -> M3f
  -> renew and fence immediately before M3g
  -> M3g index-before-log reconciliation
  -> M3h recovery audit
  -> pure worker outcome classification
  -> bounded retry policy or terminal intent
  -> final active lease fence
  -> canonical B3 retry_release or commit_terminal
```

RelayMEM compose remains queue-agnostic. It only invokes exact runtime-private checkpoint callbacks before source consumption, M3e, and M3g. The worker owns canonical queue re-read, owner/generation/token/revision/expiry fencing, lease renewal, and revision replacement after renewal.

## Technical failure versus policy meaning

M3a or M3b `blocked` is converted to a terminal memory-policy outcome only when exact private evidence proves the policy meaning:

- M3a candidate count and candidate shape are exact, with held or blocked promotion/safety policy;
- M3b contains exactly one operation with held or non-eligible preflight status.

Helper exceptions, malformed stage results, schema drift, or impossible shapes are not reclassified as policy failure. They remain blocked without a stale or false terminal queue commit.

## Retry policy

C1-2 calculates retry timing internally. The compatibility field `retry_not_before` remains present in the exact request schema, but any non-`None` caller value is rejected.

- transient lock contention: 5-second base plus deterministic bounded jitter below 5 seconds;
- verified reconciliation partial progress: 20-second base plus deterministic bounded jitter below 10 seconds;
- maximum worker attempts: 5;
- attempt-limit exhaustion becomes terminal failed with `primary_mem_retry_attempt_limit_reached`;
- retry records always contain `retry_not_before` later than their `updated_at`;
- corruption, policy hold, manual confirmation, and recovery isolation are never automatically retried.

The deterministic jitter seed uses only runtime-private job identity, claim generation, and retry class. Exact timestamps and identifiers remain absent from public projections.

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

Only exact frozen worker/source types and complete canonical B3 records are accepted. Public projections, lookalike dictionaries, bool/int confusion, wrong schemas, impossible gates, stale claims, and cross-request source reuse fail closed.

## Lease and crash behavior

M3e and M3g checkpoints use canonical B3 `renew_lease`. A successful renewal increments the record revision and replaces the worker's expected canonical record before execution continues.

Lease loss before source consumption leaves the prepared source unconsumed. Lease loss before M3e prevents page publication. Lease loss before M3g preserves an already-published page but prevents index/log mutation. Lease loss before the final transition prevents stale retry release or terminal commit.

Completed durable side effects are not rolled back. A later claim rebuilds a fresh source from the retained protected capture and converges through M3e/M3g idempotency and M3h classification.

## Public projection

The public projection and `PipelineNodeResult` expose bounded statuses, checkpoint booleans, renewal count, pipeline status, outcome transition kind, retryable/terminal booleans, queue-transition-performed, and bounded reason IDs.

They omit source messages, governed title/summary/body, page/index/log content, roots and filenames, namespace and runtime identifiers, lineage and idempotency keys, claim owner/token/revision/generation, timestamps, raw exception text, and private compose/classifier/B3 results.

## Validation

```bash
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_review_fix_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6c1_primary_worker_source_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6c1_primary_worker_outcome_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_pipeline_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_pipeline_security_smoke.py
```

## Remaining boundary

This slice still does not implement a queue scanner, automatic claim scheduler, daemon supervision, generalized worker pool, restart-complete protected source storage, later-turn recall proof, or SOUL Lab observation. Those remain subsequent I1 integration work.
