---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6_i1b_runtime_enqueue_source_capture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - ordinary request ownership changes from one run-local turn per request
  - C1-2 one-claimed-job worker source preparation changes
  - protected durable source persistence changes
  - next-turn Primary MEM recall wiring lands
relaylm_not_authoritative_for:
  - C1-0 protected worker-source schema or validator
  - B2/B3 queue record semantics
  - RelayMEM M3a-M3h composition
  - worker outcome classification
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6c1_durable_protected_source_persistence.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c2_one_queued_primary_worker_integration.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
---
# Phase 6 I1-B Runtime Enqueue and Protected Source Capture Handoff

## Status

Integration Milestone I1-B is implemented for ordinary managed non-stream and stream requests. The visible response is finalized and delivered independently, then a Starlette background task prepares the deferred source and queue artifacts.

The request thread does not claim a job, execute a worker, or call RelayMEM M3a-M3h inline.

## Runtime order

```text
ordinary managed request
  -> backend response
  -> RelayCTX visible finalization
  -> existing stream suppression / TTS observer order, when streaming
  -> HTTP body or SSE delivery
  -> post-response background finalizer
       -> exact finalized-turn protected source
       -> A1 admission
       -> A2 response-finalization handoff
       -> B1 dispatch / durable-record preflight
       -> exact claim-independent 16-field protected capture
       -> C1-5 durable protected-source commit
       -> B2 atomic content-free durable enqueue
       -> optional process-local hot-cache publication
```

The background finalizer catches bounded operational failure and never changes a response that has already been finalized. Non-stream and stream smokes verify visible output remains exact across deferred failures.

## Durability interpretation

Two crash windows are distinct:

```text
A. visible response delivered
   -> process exits before background finalizer publishes source/queue

B. source and queue published
   -> process exits before or during worker execution
```

C1-5 closes window B for protected-source recovery: every durably enqueued job has a committed protected artifact that can be rehydrated after restart.

C1-5 does not close window A. A turn that never reached durable source publication and B2 enqueue is not recoverable by source rehydration alone.

## Finalized-turn authority

The first bounded ordinary runtime owns one RelayRUN run per HTTP request and one finalized turn in that run:

```text
turn_index = 0
```

This is a run-local index, not a durable cross-request session counter. Dispatch uniqueness remains bound to exact run, lineage, session, namespace, and B1 identity.

The finalized-turn producer uses:

- exact request-local `PipelineContext`,
- exact current-user evidence retained by client-history preflight,
- final safe assistant-visible text,
- current RelaySCN scene-policy artifact,
- current RelayEMO artifact when present,
- canonical Primary source lineage,
- canonical governed-experience summary.

It does not call M3a-M3h or create a Primary page candidate. A scene persistence block fails closed.

## Exact stage handoff

`relaylm/relaymem_slp_runtime_enqueue.py` consumes only exact production results:

```text
A1 exact result
  -> A2 exact handoff
  -> B1 exact candidate
  -> C1-5 exact protected artifact publication
  -> B2 exact enqueue result
```

It does not reconstruct private data from public projections, derive dispatch identity independently, hand-write queue JSON, bypass validators, or replace B2 with direct queue access.

Disabled mode performs no content-bearing source construction and no queue I/O.

Dry-run constructs the finalized-turn source, A1/A2/B1 artifacts, and exact protected payload, but performs no durable source publication and no B2 enqueue.

Apply mode requires all explicit gates, an absolute queue root, and an absolute protected-source root. It commits the source before B2 and publishes the process-local hot cache only after B2 returns `enqueued_new` or an exactly correlated `duplicate_existing`.

## Why C1-0 construction remains claim-time

The canonical C1-0 builder accepts only an exact B3 record with `state = claimed`. Request finalization has only a B1 candidate or B2 queued record.

Therefore I1-B/C1-5 retain the exact claim-independent protected capture without fabricating a claim or directly constructing the claim-bound C1-0 dataclass.

When a real claim exists, the source preparation adapter:

1. validates the canonical claimed record and character correlation,
2. resolves the capture from the process-local hot cache or durable C1-5 artifact,
3. creates a fresh exact C1-0 request scope,
4. invokes `build_relaymem_slp_primary_worker_source` for the current claim,
5. transfers an unconsumed typed source and scope to C1-2,
6. retains the claim-independent capture until canonical terminal completion.

Each retry/new generation receives a fresh source object and one-shot scope. A consumed or stale source object remains invalid.

## Retention semantics

### Process-local hot cache

The registry remains thread-safe, capacity/TTL bounded, and fail-closed:

- expired cache entries are purged,
- capacity exhaustion rejects the new cache entry rather than evicting existing state,
- duplicate cache publication is idempotent only for exact equivalent content,
- hot-cache expiry does not delete the durable artifact.

### Durable source owner

C1-5 owns restart persistence:

- exact source schema and field set,
- job/dispatch/character binding,
- canonical integrity digest,
- safe path and file-type validation,
- no-clobber publication,
- retry/stale-recovery retention,
- fresh claim-time rehydration,
- post-terminal cleanup.

The source-before-queue order prevents a durably enqueued record from lacking its committed source artifact. A crash may leave a complete orphan artifact before B2, but an exact repeat converges idempotently.

Terminal cleanup occurs only after B3 terminal commit. Cleanup failure is reported without rolling back queue state.

## Audit projection

Public/audit surfaces contain only bounded schemas, statuses, booleans, counts, failure-stage enums, and reason IDs.

They exclude:

- user or assistant text,
- governed title/summary/body,
- namespace values,
- run/session/job/dispatch identifiers,
- lineage and idempotency keys,
- queue/source paths,
- source digests,
- timestamps,
- exception text,
- protected nested results.

## Validation

```bash
PYTHONPATH=. python scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6_runtime_enqueue_app_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6c1_primary_worker_source_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_durable_protected_source_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
```

## Remaining I1 boundary

I1-B, C1-2, C1-4, C1-5, and C2 are implemented. C2 accepts one exact queued canonical record, performs canonical B3 claim, rehydrates through C1-5, and invokes C1-2 without adding a scanner, daemon, generalized scheduler, or visible-response coupling.

The next bounded boundary is next-turn recall with character/namespace isolation. Real SOUL Lab observation, one auditable Correct operation, and an explicit decision for the pre-enqueue background-finalizer crash window remain later I1 work.
