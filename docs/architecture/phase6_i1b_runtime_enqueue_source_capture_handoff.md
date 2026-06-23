---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6_i1b_runtime_enqueue_source_capture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - ordinary request ownership changes from one run-local turn per request
  - C1-2 one-claimed-job worker consumes process-local source captures
  - protected durable source persistence lands
  - next-turn Primary MEM recall wiring lands
relaylm_not_authoritative_for:
  - C1-0 protected worker-source schema or validator
  - B2/B3 queue record semantics
  - RelayMEM M3a-M3h composition
  - worker outcome classification
---
# Phase 6 I1-B Runtime Enqueue and Protected Source Capture Handoff

## Status

Integration Milestone I1-B is implemented for ordinary managed non-stream and
stream requests. The visible response is finalized and delivered independently,
then a Starlette background task prepares the deferred queue/source artifacts.
The request thread does not claim the job, execute a worker, or call the RelayMEM
M3a-M3h compose boundary.

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
       -> exact 16-field C1-0 payload assembly
       -> B2 atomic durable enqueue
       -> process-local protected source registry publication
```

The background finalizer catches bounded operational failure and never changes a
response that has already been finalized. Non-stream tests verify the JSON body
remains exact after enqueue failure. Stream tests verify every backend SSE byte,
including `[DONE]`, remains exact.

This response-independent design has one explicit live-process durability gap:
if the process exits after visible response delivery but before the Starlette
background task completes, no durable enqueue or protected source publication is
guaranteed for that turn. That gap is distinct from losing an already-published
process-local source after restart. Later I1 restart-completion work must cover
both the pre-enqueue background-task window and post-enqueue protected-source
recovery; a durable source/finalization owner must not describe only registry
rehydration.

## Finalized-turn authority

The first bounded ordinary runtime owns one RelayRUN run per HTTP request and one
finalized turn in that run. Its exact run-local turn authority is therefore:

```text
turn_index = 0
```

This value is not a cross-request counter and is not presented as durable session
turn history. Dispatch uniqueness remains bound to the existing exact run ID,
request-derived lineage, session, namespace, and B1 dispatch identity.

The finalized-turn producer uses:

- the exact request-local `PipelineContext`;
- the exact current-user message retained by
  `ClientHistoryExclusionPreflightResult`;
- the final safe assistant-visible text;
- the current RelaySCN scene-policy artifact;
- the current RelayEMO artifact, when present;
- `build_relaymem_primary_source_lineage` for canonical lineage;
- `build_relaymem_governed_experience_summary` for the existing governed
  experience schema.

It does not call the M3c page-candidate builder or any M3a-M3h persistence stage.
A RelaySCN persistence block prevents source readiness and fails closed with the
bounded reason `scene_persistence_blocked`.

## Exact stage handoff

`relaylm/relaymem_slp_runtime_enqueue.py` accepts only the exact
`RelayMEMSLPFinalizedTurnSourceResult`. It passes the exact production result of
each phase to the next phase:

```text
A1 exact result -> A2 exact handoff -> B1 exact candidate -> B2 exact result
```

It does not reconstruct private data from public projections, derive dispatch
identity independently, hand-write queue JSON, bypass validators, or replace B2
with direct filesystem access.

Disabled mode performs no content-bearing source construction and no queue I/O.
Dry-run constructs the finalized-turn source, A1/A2/B1 artifacts, and exact
protected payload, but performs no B2 enqueue and no registry publication. Apply
mode requires all three explicit gates and publishes the source only after B2
reports `enqueued_new` or an exactly correlated `duplicate_existing`.

## Why typed C1-0 construction remains claim-time

The canonical C1-0 builder accepts only an exact B3 record with
`state = claimed`. Request finalization has only a B1 candidate or B2 queued
record. The runtime therefore retains the exact protected 16-field payload and
an exact C1-0 request scope without fabricating a claim or directly constructing
the C1 dataclass.

When C1-2 later presents the real claimed record, the registry:

1. validates the canonical claimed record and character correlation;
2. invokes `build_relaymem_slp_primary_worker_source` with that record;
3. invokes `consume_relaymem_slp_primary_worker_source` exactly once;
4. transfers the typed source and scope to the worker;
5. removes the capture from the registry.

Until that sequence occurs, public diagnostics report `worker_ready = false`.

## Retention semantics

The registry is thread-safe, process-local, explicitly not restart-complete, and
bounded by an exact entry-count limit plus a monotonic TTL. It exposes exact
publish, consume-for-claim, and release operations.

Its bounded policy is fail-closed rather than eviction-based:

- expired entries and entries whose request scope is already inactive are purged
  before size, publish, consume, or release decisions;
- purge closes the retained C1-0 request scope;
- when the entry-count limit remains full after purge, a new publication is
  rejected with `protected_source_registry_capacity_reached`;
- a capacity rejection never evicts or overwrites an existing capture;
- a claim after TTL expiry or explicit release receives
  `protected_source_unavailable` through the normal source-unavailable path.

Duplicate publication is idempotent only when character and protected payload
are exactly equivalent. A same-dispatch different-source payload fails closed
and never overwrites the existing capture. Successful consume removes the
capture and transfers scope ownership to the worker.

A durable queue record may remain after source-retention failure because B2 has
already committed it. The runtime reports `source_retention_failed`, keeps
`worker_ready = false`, and never copies protected content into the queue record,
trace, log, public error, response, or PipelineNodeResult. Capacity exhaustion,
TTL expiry, explicit release, process restart, and a missing post-response task
must all remain distinguishable from durable worker success.

The runtime source-capture smoke covers capacity rejection, monotonic-TTL purge,
and consume-after-removal source-unavailable behavior. The C1 worker acceptance
matrix additionally requires a claimed job with no source to fail closed without
calling C1-1 or committing durable success.

## Audit projection

The generic trace registry explicitly recognizes only:

```text
relaymem_slp_runtime_enqueue
relaymem_slp_finalized_turn_source
relaymem_slp_runtime_enqueue
```

The persisted projection contains bounded schemas, statuses, booleans, counts,
failure-stage enums, and reason IDs only. It excludes user/assistant text, title,
summary, namespace values, run/session/job/dispatch identifiers, lineage,
idempotency keys, queue paths, timestamps, exception text, and protected nested
results. Unknown nodes and fields continue to be omitted by the fail-closed audit
projection.

## Validation

```bash
python -m compileall -q \
  relaylm/app.py \
  relaylm/audit_projection.py \
  relaylm/trace_runtime.py \
  relaylm/relaymem_slp_finalized_turn_source.py \
  relaylm/relaymem_slp_runtime_finalization.py \
  relaylm/relaymem_slp_runtime_enqueue.py \
  relaylm/relaymem_slp_primary_worker_source_registry.py \
  scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py \
  scripts/relaylm_phase6_runtime_enqueue_app_smoke.py

PYTHONPATH=. python scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6_runtime_enqueue_app_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_slp_job_admission_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_slp_response_handoff_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b1_dispatch_preflight_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_enqueue_lifecycle_compat_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6c1_primary_worker_source_smoke.py
PYTHONPATH=. python scripts/relaylm_relayctx_unpack_runtime_app_smoke.py
PYTHONPATH=. python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
```

## Remaining I1 boundary

Worker execution remains unimplemented on `main`. The next boundary is C1-2:
execute one already-claimed job using the exact C1-0 source, the merged RelayMEM
M3a-M3h compose boundary, the pure worker-outcome classifier, and B3 fenced retry
or terminal transitions. Restart-complete protected source persistence, coverage
of the post-response task crash window, and next-turn Primary MEM recall remain
later I1 work.
