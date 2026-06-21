---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6b1_relayslp_dispatch_preflight
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-B1 dispatch-key or durable-job candidate schema changes
  - Phase 6-B2 atomic durable enqueue lands
  - A2 enqueue-candidate schema changes
relaylm_not_authoritative_for:
  - RelayMEM memory meaning or memory-write idempotency
  - durable queue storage backend
  - duplicate lookup or collision handling
  - claim lease retry or terminal-state mutation
  - worker RelaySLP execution
  - page index or log apply
  - RelaySOUL mutation
  - request-runtime wiring
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - relaymem_slp_current_target.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# Phase 6-B1 RelaySLP Dispatch Preflight

## Status

Phase 6-B1 is implemented as a default-off, helper-only, read-only, dry-run-only dispatch and durable-job-record preflight.

```text
exact runtime-private A2 result
  -> exact A2 enqueue-candidate revalidation
  -> versioned canonical dispatch identity
  -> deterministic separate job identity
  -> runtime-private queued durable-job candidate
  -> content-free queue status projection
```

B1 performs no queue I/O, duplicate lookup, enqueue, claim, lease, retry, worker invocation, RelaySLP execution, memory write, RelaySOUL mutation, or visible-response change.

## Public helper

```python
build_relaymem_slp_dispatch_preflight(
    handoff_result,
    enabled=False,
    dry_run_only=True,
)
```

Related schemas:

```text
relaymem.slp_dispatch_preflight.v0
relaymem.slp_durable_job.v0
relaymem.slp_queue_status_projection.v0
relaymem.slp_dispatch_key.v0
relaymem.slp_job_id.v0
```

A durable-job candidate is created only when `enabled=true` and `dry_run_only=true` and the exact A2 result passes every B1 validation gate.

## Direct A2 consumption

B1 accepts only an exact in-process `RelayMEMSLPResponseHandoffResult`. A dictionary returned by `to_runtime_dict()`, a public projection, `PipelineNodeResult`, trace record, frontend metadata object, or lookalike mapping is rejected.

The A2 result must be the exact successful dry-run handoff shape:

```text
status = dry_run_candidate
enabled = true
dry_run_only = true
response_finalized = true
candidate_count = 1
candidate_created = true
blocked_reasons = []
```

Its queue, worker, RelaySLP, memory, SOUL, and visible-response side-effect flags must all remain false.

The runtime-private candidate must be the exact `RelayMEMSLPEnqueueCandidate` type and exact `relaymem.slp_enqueue_candidate.v0` field set. B1 rejects unknown or missing fields, non-strict booleans and integers, unsupported trigger/stage/event values, malformed correlation or namespace tokens, invalid source count or lineage fingerprint, pre-existing side effects, and non-empty dispatch or memory-write idempotency keys.

## Dispatch identity

B1 owns the first generated dispatch identity. The version is:

```text
relaymem.slp_dispatch_key.v0
```

The canonical ordered input is exactly:

```text
dispatch_key_version
candidate_schema_version
candidate_kind
trigger_mode
processing_stage
source_event_kind
run_id
turn_index
session_id presence marker
session_id value or empty sentinel
namespace
source_count
source_lineage_fingerprint
```

B1 encodes that ordered structure as compact deterministic JSON with ASCII escaping and hashes the UTF-8 bytes with SHA-256.

The runtime-private key format is:

```text
slp-dispatch-v0:<64 lowercase hexadecimal characters>
```

The derivation excludes source-admission status, runtime terminal status, persistence-policy status, timestamps, random values, queue paths, record revision, attempt count, claim/lease metadata, retry/failure state, memory-write idempotency, and raw content. Therefore operational-status changes do not create a second logical dispatch identity.

## Job identity

`job_id` is separate from the dispatch key and is never an input to it.

B1 deterministically derives the job identifier by hashing a separate domain string plus the completed dispatch key:

```text
relaymem.slp_job_id.v0 NUL <dispatch-idempotency-key>
```

The runtime-private job format is:

```text
slp-job-v0:<64 lowercase hexadecimal characters>
```

This keeps record identity deterministic for B2 while preserving explicit domain separation from dispatch identity and RelayMEM memory-write identity.

## Durable-job candidate

B1 emits one runtime-private `relaymem.slp_durable_job.v0` candidate. It copies only revalidated A2 source fields and initializes only Phase 6-owned queue-control fields.

Initial state is:

```text
state = queued
record_revision = 0
created_at = null
updated_at = null
attempt_count = 0
claim_generation = 0
claim_owner = ""
lease_token = ""
lease_acquired_at = null
lease_expires_at = null
retry_class = unclassified
retry_not_before = null
failure_class = none
terminal_reason_id = ""
```

B1 does not assign durable timestamps. B2 assigns `created_at` and `updated_at` only as part of atomic durable enqueue.

The A2 candidate does not carry queue retry policy. B1 therefore initializes `retry_class=unclassified`; it does not recover A1 retry metadata or infer retry policy from the processing stage.

## Idempotency separation

The generated dispatch key is never copied into a RelayMEM memory-write field. The A2 memory-write idempotency field must be empty before B1 runs.

```text
Phase 6 dispatch idempotency
  -> deferred job identity and duplicate enqueue prevention

RelayMEM memory-write idempotency
  -> durable memory apply identity
```

B1 creates only the first domain. It neither requests nor performs a memory write.

## Content-free projection

The public/default diagnostics schema is `relaymem.slp_queue_status_projection.v0` and contains only the B0 allowlist:

```text
schema_version
status
state
trigger_mode
processing_stage
source_event_kind
source_count
attempt_count
retry_class
response_finalized
enqueue_attempted
enqueue_applied
duplicate_detected
claim_active
lease_present
terminal
failure_class
blocked_reason_ids
```

It excludes the durable-job body, A2/B1 candidates, job and dispatch identifiers, run/turn/session/namespace values, lineage fingerprint, exact timestamps, claim owner, lease token, queue paths, memory-write idempotency keys, and raw content.

The optional `PipelineNodeResult` uses node name `relaymem_slp_dispatch_preflight` and omits the runtime-private candidate and identifiers.

## Preserved non-goals

Phase 6-B1 does not:

- read or write a queue backend,
- check whether a dispatch key already exists,
- classify duplicate versus collision,
- assign durable timestamps,
- create directories or files,
- claim work or create lease tokens,
- transition queue state,
- execute retries or recovery,
- invoke a scheduler, worker, RelaySLP, or RelayMEM apply helper,
- write Primary or Secondary MEM,
- update memory pages, index, or log,
- mutate RelaySOUL,
- wire request runtime,
- delay or alter the finalized visible response,
- execute TTS, audio, avatar, or Live2D behavior.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_slp_dispatch_preflight.py \
  scripts/relaylm_phase6b1_dispatch_preflight_smoke.py \
  scripts/relaylm_phase6b1_dispatch_preflight_security_smoke.py

PYTHONPATH=. python scripts/relaylm_phase6b1_dispatch_preflight_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b1_dispatch_preflight_security_smoke.py
```

Coverage includes default-off and strict dry-run gates, exact direct A2 type/shape validation, deterministic dispatch and job identities, session-presence identity, operational-status exclusions, fixed queued/retry initialization, strict dispatch/memory-write separation, unknown-field and side-effect rejection, content-free projections, and absence of queue/worker/memory/SOUL/visible-response side effects.

## Phase 6-B2 implementation handoff

Phase 6-B2 consumes only an exact validated B1 result and runtime-private durable-job candidate. It adds gated atomic create-if-absent persistence, assigns durable timestamps, and distinguishes `enqueued_new`, `duplicate_existing`, `blocked_collision`, `blocked_corrupt`, and `write_failed` without worker invocation.

The next bounded slice is Phase 6-B3 claim/lease/retry-release/stale-recovery/terminal-state helpers. Worker execution remains later.
