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
  - I1-G durable-finalization publication or replay changes
  - RT-1 Primary writer admission or retirement changes downstream execution meaning
relaylm_not_authoritative_for:
  - C1-0 protected worker-source schema or validator
  - B2/B3 queue record semantics
  - RelayMEM M3a-M3h composition
  - worker outcome classification
  - I1-G durable-finalization replay, retention, or crash-validation semantics
  - RT-1 cutover state, Primary writer authorization, or retirement approval
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6c1_durable_protected_source_persistence.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c2_one_queued_primary_worker_integration.md
  - ../contracts/slp/durable-queue.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../PROJECT_STATUS.md
---
# Phase 6 I1-B Runtime Enqueue and Protected Source Capture Handoff

Last reviewed: 2026-08-08 JST

## Status

Integration Milestone I1-B is implemented for ordinary managed non-stream and stream requests. The visible response is finalized and delivered independently, then the ordinary finalization path prepares the deferred source and queue artifacts through the existing I1-B/C1-5/B2 authorities.

I1-B defines finalized-turn meaning, exact source capture, and enqueue handoff. It does not grant Primary writer permission. Under current RT-1D-R4 semantics, any later C2/C1-2/C1-1 Primary execution still requires the exact caller-carried Primary writer decision owned by the cutover domain.

The request thread does not claim a job, execute a worker, or call RelayMEM M3a-M3h inline.

## Runtime order

The original ordinary I1-B path is:

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

I1-G later added a pre-release durable-finalization layer around this same finalized-turn meaning. Its completed GA-GE authority may durably seal evidence before protected visible release and converge the same C1-5/B2 handoff through normal finalization or caller-selected replay. I1-B remains the finalized-turn/source-capture authority and does not redefine I1-G replay, retention, or crash-validation semantics.

Neither the original post-response path nor the later I1-G convergence path carries a Primary writer decision as part of the I1-B source/enqueue artifact. Durable source/queue availability is therefore evidence and deferred-work availability, not authorization to execute a Primary writer.

## Durability interpretation

Two historical crash windows are distinct:

```text
A. visible response delivered
   -> process exits before background finalizer publishes source/queue

B. source and queue published
   -> process exits before or during worker execution
```

C1-5 closes window B for protected-source recovery: every durably enqueued job has a committed protected artifact that can be rehydrated after restart.

C1-5 by itself does not close historical window A. I1-GA through I1-GE were completed later and now own the resolved pre-enqueue durable-finalization publication/replay/retention/crash-validation boundary for that window. This I1-B handoff records the historical source-capture limitation but is not authority for I1-G mechanics.

Recovery of either window does not imply Primary worker execution. Once source/queue evidence is available, B3/C2/C1 still apply their own lifecycle and writer-decision gates.

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

The resulting finalized-turn evidence may be durably retained/enqueued even though a later Primary writer is not permitted. Formation/mutation authority is decided only at the downstream execution boundaries; I1-B evidence construction does not infer writer permission from content quality, scene admission, queue identity, or prior Primary success.

## Exact stage handoff

`relaylm/relaymem_slp_runtime_enqueue.py` consumes only exact production results:

```text
A1 exact result
  -> A2 exact handoff
  -> B1 exact candidate
  -> C1-5 exact protected artifact publication
  -> B2 exact enqueue result
```

It does not reconstruct private data from public projections, derive dispatch identity independently, hand-write queue JSON, bypass validators, replace B2 with direct queue access, or resolve RT-1 writer authorization.

Disabled mode performs no content-bearing source construction and no queue I/O.

Dry-run constructs the finalized-turn source, A1/A2/B1 artifacts, and exact protected payload, but performs no durable source publication and no B2 enqueue.

Apply mode requires all explicit enqueue/source gates, an absolute queue root, and an absolute protected-source root. It commits the source before B2 and publishes the process-local hot cache only after B2 returns `enqueued_new` or an exactly correlated `duplicate_existing`.

These I1-B modes govern source/enqueue mechanics only. They do not convert a rejected RT-1 Primary writer decision into permission, and I1-B does not add a writer-decision field to its durable source or queue records.

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

A fresh source/claim is still not writer permission. C2/C1-2/C1-1 independently require the exact RT-1 writer decision for the later invocation; rehydration cannot revive Primary mutation authority after `primary_writer_fenced`.

## Retention semantics

### Process-local hot cache

The registry remains thread-safe, capacity/TTL bounded, and fail-closed:

- expired cache entries are purged,
- capacity exhaustion rejects the new cache entry rather than evicting existing state,
- duplicate cache publication is idempotent only for exact equivalent content,
- hot-cache expiry does not delete the durable artifact.

A hot-cache hit is an evidence-availability optimization only and never an authorization signal.

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

C1-5 durability, B2 queue presence, retryability, and idempotent duplicates preserve evidence/work only. None grants downstream Primary writer permission.

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
- private writer-decision identity,
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

The I1-B smokes remain authority for finalized-turn/source/enqueue behavior and visible-response independence. Separate C2/C1 worker regressions prove that a foreign/non-permitted writer decision fails closed before Primary claim/source/worker or pipeline execution. I1-G authority and its dedicated tests separately prove the completed pre-enqueue durable-finalization recovery window.

## Current downstream boundary

I1-B, C1-2, C1-4, C1-5, C2, Phase I-1 next-turn recall/scope isolation, Phase I-2 observation, Phase I-3 Correct, and I1-GA through I1-GE were completed through their separate authorities. Those implementation facts are not an unconditional Primary runtime path after RT-1D-R4.

For retained Primary compatibility work, source/queue evidence created by I1-B/C1-5/B2 may proceed to C2/C1 only when the exact downstream writer decision permits mutation. A rejected decision leaves evidence/work state governed by its existing owners but does not authorize Primary formation.

RT-1D-R5/R6 own final retirement or explicitly retained historical/read-only/test disposition of the replaced Primary worker/source/enqueue surfaces. This I1-B handoff does not pre-authorize deletion, alter I1-G status, or restore reader/writer authority from historical completion evidence.
