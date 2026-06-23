---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6_i1b_runtime_enqueue_source_capture
relaylm_status: current
relaylm_volatility: high
relaylm_owner: implementation
relaylm_update_trigger:
  - ordinary managed runtime gains an authoritative turn index owner
  - governed-experience production is connected before request finalization
  - C1-2 one-claimed-job worker consumes process-local source captures
  - protected durable source persistence lands
relaylm_not_authoritative_for:
  - C1-0 protected worker-source schema or validator
  - B2/B3 queue record semantics
  - RelayMEM M3a-M3h composition
  - worker outcome classification
---
# Phase 6 I1-B Runtime Enqueue and Protected Source Capture Handoff

## Implemented bounded boundary

This slice adds two production modules without changing the C1-0 source schema,
builder, validator, projection, or one-shot consumption contract:

- `relaylm/relaymem_slp_runtime_enqueue.py`
- `relaylm/relaymem_slp_primary_worker_source_registry.py`

The orchestration helper preserves the exact production chain:

```text
A1 admission result
  -> A2 response-finalization handoff
  -> B1 dispatch and durable-record candidate
  -> exact protected 16-field source payload assembly
  -> B2 atomic durable enqueue
  -> process-local protected source capture publication
```

Disabled mode performs no content-bearing capture and no queue I/O. Dry-run mode
constructs the exact A1/A2/B1 artifacts and protected source payload but performs
neither B2 enqueue nor registry publication. Apply mode publishes the protected
capture only after B2 reports `enqueued_new` or an exactly correlated
`duplicate_existing` record.

The integrated public projection is content-free. It excludes message content,
title, summary, namespace values, run/session/job/dispatch identifiers, lineage,
queue paths, timestamp values, and exception text. It also states explicitly
that the typed source is not yet built, the worker is not ready, no B3 claim was
performed, no worker was invoked, and source persistence is not restart-complete.

## Why typed C1-0 construction is deferred

The merged C1-0 production builder accepts only an exact canonical B3 record
with `state = claimed`. Request finalization has only a B1 candidate or a B2
`queued` record. Fabricating a claimed record, directly instantiating the source
dataclass, reconstructing it from a public projection, or weakening the C1-0
validator would violate the current contract.

Therefore the process-local registry retains the exact protected payload and an
exact C1-0 request scope. When a later worker presents the real claimed record,
the registry:

1. validates the canonical claimed record and exact character correlation;
2. invokes `build_relaymem_slp_primary_worker_source` with that real record;
3. invokes `consume_relaymem_slp_primary_worker_source` exactly once;
4. transfers the protected typed source and scope to the worker;
5. removes the capture from the registry.

This keeps the content-free queue record separate from protected content and
prevents a source from becoming worker-ready without a real B3 claim.

## Remaining ordinary-runtime prerequisites

The repository does not yet expose two authoritative inputs required to call the
new helper from `app.py` or the stream-final observer:

1. an ordinary managed-turn `turn_index` owner; and
2. a pre-finalization producer of the exact governed-experience artifact required
   by C1-0.

The only current governed-experience builder is part of the RelayMEM M3c page
candidate boundary. Calling it during request finalization would violate the
explicit rule that M3a-M3h must not run inline. Creating a second lookalike
schema or hand-written compatibility artifact would also violate the C1-0
ownership boundary.

For that reason this change does not add a misleading `app.py` call that can
never safely reach apply mode. Ordinary non-stream and stream wiring remains
blocked until those two authoritative inputs are provided. Visible response
behavior is unchanged.

## Retention semantics

The registry is thread-safe, bounded by entry count and monotonic TTL, and
process-local only. It provides explicit publish, consume-for-claim, and release
operations. Duplicate publication is idempotent only when the character and
entire protected payload are equivalent; the existing capture is never
overwritten. A same-dispatch different-source payload fails closed. Expiry and
release close the retained C1-0 request scope. Successful consume transfers the
scope to the worker, which must close it after use.

A queue record may remain after source-retention failure because B2 publication
is already durable. The integration result reports this as
`source_retention_failed`; it never reports the job as worker-ready and never
copies protected content into the queue record or trace.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_slp_runtime_enqueue.py \
  relaylm/relaymem_slp_primary_worker_source_registry.py \
  scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py

PYTHONPATH=. python scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_slp_job_admission_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_slp_response_handoff_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b1_dispatch_preflight_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_enqueue_lifecycle_compat_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6c1_primary_worker_source_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
```

## Next integration boundary

Resolve the authoritative managed-turn index and governed-experience producer,
then wire this helper after non-stream response finalization and after the
existing stream-final suppression/TTS observer chain. The following runtime
slice remains C1-2: execute one already-claimed job using the exact typed source,
Thread D's M3a-M3h compose result, Thread B's outcome classifier, and B3 fenced
transition helpers.
