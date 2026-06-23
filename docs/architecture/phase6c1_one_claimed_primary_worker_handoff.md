---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_one_claimed_primary_worker
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - one-claimed Primary MEM worker request, result, projection, or lease checkpoint semantics change
  - ordinary request-runtime source adapter is integrated
  - protected source persistence or scheduler ownership is implemented
relaylm_not_authoritative_for:
  - ordinary app.py or stream-final request-runtime source capture
  - authoritative turn-index allocation or governed-experience production
  - queue scanning, scheduling, daemon, worker pool, or backoff policy
  - protected source persistence, restart rehydration, retention, or cleanup
  - RelayMEM page, index, or log semantics owned by M3a-M3h
  - Secondary MEM, RelaySOUL mutation, or SOUL Lab runtime behavior
relaylm_related_authority:
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

The caller supplies one exact claimed record, one exact C1-0 protected worker source, its current request-local scope, the queue root, and the RelayMEM store root. The worker does not scan the queue, select jobs, reconstruct source content, allocate a turn index, or depend on the Draft PR #365 request-runtime registry.

## Implemented runtime sequence

The worker fixes this order:

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
  -> final active lease fence
  -> canonical B3 retry_release or commit_terminal
```

RelayMEM compose remains queue-agnostic. It only invokes exact runtime-private checkpoint callbacks before source consumption, M3e, and M3g. The worker owns canonical queue re-read, owner/generation/token/revision/expiry fencing, B3 lease renewal, and revision replacement after renewal.

## Exact boundaries

Production module:

```text
relaylm/relaymem_slp_primary_worker.py
```

Schemas:

```text
relaymem.slp_primary_worker_request.v0
relaymem.slp_primary_worker_result.v0
relaymem.slp_primary_worker_projection.v0
```

Only the exact frozen worker request, exact canonical B3 claimed record, exact `RelayMEMSLPPrimaryWorkerSource`, and exact `RelayMEMSLPPrimaryWorkerSourceScope` are accepted. Generic dictionaries, public projections, classifier lookalikes, checkpoint lookalikes, bool/int confusion, wrong schemas, impossible gates, invalid roots, stale claims, and cross-request source reuse fail closed.

The apply gate is exactly:

```text
enabled = true
dry_run_only = false
apply_enabled = true
```

Disabled mode performs no source consumption, compose execution, memory mutation, or B3 transition. Dry-run validates the exact request, active claim, and source correlation, executes compose in dry-run mode, and performs no M3e, M3g, or queue mutation. It does not claim durable success.

## Lease and crash behavior

M3e and M3g checkpoints use the canonical B3 `renew_lease` transition. A successful renewal increments the canonical record revision; the worker replaces its expected record with the returned durable record before continuing.

Lease loss before source consumption leaves the source unconsumed and performs no M3 stage or queue transition. Lease loss before M3e prevents page publication. Lease loss before M3g preserves an already-published page but prevents index/log mutation. Lease loss before the final queue transition prevents stale retry release or terminal commit.

Completed durable side effects are not rolled back. Later claims converge through the existing M3e/M3g idempotency and M3h recovery classification boundaries.

## Outcome mapping

The worker invokes the production pure classifier and does not reimplement its result mapping.

- verified durable success commits B3 `succeeded` with reason `primary_mem_durable_state_verified`
- lock contention and verified reconciliation partial progress use B3 `retry_release`
- policy held/blocked, manual confirmation, recovery isolation, corruption, conflict, and divergence commit B3 `failed` with the classifier-owned failure class and reason
- invalid or inconsistent classifier input performs no unsafe queue transition
- no `dead_letter` state is introduced

## Public projection

The public projection and `PipelineNodeResult` are deterministic and content-free. They expose bounded statuses, checkpoint booleans, renewal count, pipeline status, outcome transition kind, retryable/terminal/success/failure booleans, queue-transition-performed, and bounded reason IDs.

They omit source messages, governed title/summary/body, page/index/log content, roots and filenames, namespace and runtime identifiers, lineage and idempotency keys, owner/token/revision/generation, timestamps, retry timestamp, raw exception text, and private compose/classifier/B3 results. Content-bearing dataclass fields are excluded from `repr`.

## Explicitly not implemented

The following remain outside this slice:

- ordinary `app.py` and stream-final observer wiring
- authoritative `turn_index` allocation
- governed-experience producer
- Draft PR #365 registry/capture/handoff integration
- durable protected-source persistence or restart rehydration
- queue scanner, scheduler, daemon, generalized worker pool, and thread management
- backoff or jitter engine
- source cleanup daemon
- next-turn retrieval or RelayCTX memory injection
- SOUL Lab API, authoritative memory correction, RelaySOUL mutation, Secondary MEM, TTS, audio, Live2D, or avatar execution

Issue #366 therefore remains open and does not block this already-claimed worker boundary.

## Next integration point

A later adapter may combine the completed ordinary request-runtime source capture boundary with a real B3 claimed record and construct the exact C1-0 source plus this worker request. Alternatively, C1-4 may add an integrated worker smoke. The worker itself remains independent of that adapter and of any process-local registry.
