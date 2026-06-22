---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6b3_relayslp_queue_state_helpers
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-B3 queue transition request or result schema changes
  - durable queue state or fencing semantics change
  - Phase 6-C worker execution lands
  - queue backend or locking semantics change
relaylm_not_authoritative_for:
  - RelayMEM memory meaning or memory-write idempotency
  - retry budget or backoff policy
  - worker RelaySLP execution
  - request-runtime enqueue wiring
  - Primary or Secondary MEM formation or apply
  - RelaySOUL mutation
  - TTS audio or avatar execution
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - relaymem_slp_current_target.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# Phase 6-B3 RelaySLP Fenced Queue State Helpers

## Status

Phase 6-B3 is implemented as a default-off, dry-run-first, helper-only queue-control boundary over complete canonical Phase 6-B2 durable records.

It provides exactly five transitions:

```text
claim
renew_lease
retry_release
stale_recovery
commit_terminal
```

The next RelayLM Core boundary is Phase 6-C worker execution under an exact active lease fence.

```text
B2 canonical durable queued record
  -> B3 exact runtime-private transition request
  -> secure locked read and complete record revalidation
  -> fenced transition proposal
  -> dry-run result or atomic compare-and-swap replacement
  -> content-free queue status projection
  -> Phase 6-C worker execution: next
```

B3 does not execute a worker, invoke RelaySLP, decide retry policy, form or write MEM, mutate RelaySOUL, wire request runtime, or change a visible response.

## Public helper boundary

```python
transition_relaymem_slp_queue_state(
    request,
    queue_root=...,
    enabled=False,
    dry_run_only=True,
    apply_enabled=False,
)
```

The exact runtime-private types are:

```text
RelayMEMSLPQueueTransitionRequest
RelayMEMSLPQueueStateTransitionResult
```

The schema identifiers are:

```text
relaymem.slp_queue_transition_request.v0
relaymem.slp_queue_state_transition.v0
relaymem.slp_durable_job.v0
relaymem.slp_queue_status_projection.v0
```

Apply occurs only when all gates are exact booleans and all are satisfied:

```text
enabled = true
dry_run_only = false
apply_enabled = true
```

`enabled=false` performs no queue I/O. `enabled=true` with `dry_run_only=true` performs a shared-lock inspection and returns a runtime-private proposed record without disk mutation. `dry_run_only=false` with `apply_enabled=false` is blocked rather than silently applying.

## Exact transition request

The request contains exactly typed runtime-private control values:

```text
transition_kind
job_id
dispatch_idempotency_key
expected_record_revision
expected_state
claim_owner
claim_generation
lease_token
lease_duration_seconds
retry_class
retry_not_before
failure_class
terminal_state
terminal_reason_id
```

The helper accepts only the exact in-process dataclass. A dictionary returned by `to_runtime_dict()`, a public projection, trace record, frontend object, or lookalike class is rejected.

The request job ID is re-derived from the dispatch key before any queue path is opened. The dispatch key is the only identity used to derive the deterministic record filename. Job ID, owner, token, retry values, terminal reason, and caller-supplied strings never participate in path construction.

## Complete durable-record revalidation

Every operation reads and revalidates the complete canonical `relaymem.slp_durable_job.v0` shape. Validation includes:

- the exact 32-field set and exact schema versions,
- strict bool/int separation for all counters,
- bounded ASCII tokens and source counts,
- deterministic dispatch-key re-derivation,
- deterministic job-ID re-derivation,
- canonical six-microsecond UTC timestamps ending in `Z`,
- `updated_at >= created_at`,
- non-negative bounded revision, attempt, and generation counters,
- `attempt_count == claim_generation`,
- `record_revision >= claim_generation`,
- state-specific claim, lease, retry, failure, and terminal invariants,
- deterministic dispatch-digest filename agreement.

Unknown fields, missing fields, duplicate JSON keys, malformed UTF-8, malformed JSON, non-canonical JSON bytes, non-finite numbers, schema drift, identity mismatch, impossible state combinations, and counter or timestamp inconsistencies fail closed.

B3 never repairs, normalizes, overwrites, or passes a corrupt record onward.

## Transition semantics

### `claim`

Source state must be `queued` with the exact expected revision, state, job identity, dispatch identity, and current claim generation.

If `retry_not_before` is later than the current UTC time, the result is `not_ready`. Equality is ready.

A successful claim atomically:

```text
state = claimed
record_revision += 1
attempt_count += 1
claim_generation += 1
claim_owner = request claim owner
lease_token = new opaque unpredictable token
lease_acquired_at = current UTC time
lease_expires_at = current UTC time + bounded lease duration
retry_not_before = null
```

Attempt, generation, revision, and timestamp overflow are bounded failures. A claim never accepts a caller-supplied lease token.

### `renew_lease`

Source state must be `claimed`. Renewal fences on the exact:

```text
record_revision
state
claim_owner
claim_generation
lease_token
```

An already expired lease is not renewed. The result is `not_ready` with a stale-recovery-required reason. Expiry equality is expired.

Renewal increments only `record_revision`, updates `updated_at`, and resets `lease_expires_at` to the validated current UTC transition time plus the bounded requested lease duration. It does not accumulate duration from the previous expiry. It preserves attempt count, claim generation, owner, lease token, and lease acquisition time. Timestamp arithmetic overflow and clock regression are returned as bounded blocked results rather than exceptions.

### `retry_release`

Source state must be an active, unexpired `claimed` lease. It uses the same exact owner/generation/token fence as renewal.

B3 does not decide retry budget, policy, or backoff. It records only the bounded classification metadata supplied by its trusted caller.

A successful release atomically:

```text
state = queued
record_revision += 1
claim_owner = ""
lease_token = ""
lease_acquired_at = null
lease_expires_at = null
retry_class = request retry class
retry_not_before = request retry timestamp or null
failure_class = request failure class
```

Attempt count and claim generation are preserved.

### `stale_recovery`

Source state must be `claimed`. Recovery requires the exact revision, state, claim generation, and lease token, but intentionally does not require owner equality.

Before lease expiry, recovery is `not_ready`. At the exact expiry instant and afterward, the lease is stale.

A successful stale recovery atomically:

```text
state = queued
record_revision += 1
claim and lease fields cleared
attempt_count preserved
claim_generation preserved
retry_class = stale_lease_recovery
retry_not_before = null
failure_class = stale_lease_expired
```

A subsequent claim increments attempt and generation again. The covered sequence proves:

```text
record_revision == 3
attempt_count == 2
claim_generation == 2
```

### `commit_terminal`

From an active `claimed` lease, terminal commit requires the exact revision, state, owner, generation, and lease token. Allowed targets are:

```text
succeeded
failed
cancelled
```

From `queued`, only `cancelled` is allowed and all claim fence fields must be empty.

A terminal commit increments revision, clears claim/lease and retry-ready metadata, records the bounded terminal reason, and records a non-`none` failure class only for `failed`.

B3 never generates `dead_letter`. A pre-existing strict `dead_letter` record is recognized only as terminal and immutable. No transition is allowed out of `succeeded`, `failed`, `cancelled`, or `dead_letter`.

## Locking and filesystem safety

The caller supplies one absolute, pre-existing queue root. B3 walks every path component from the filesystem anchor with directory file descriptors and rejects symlinks, missing components, non-directories, inode changes, unsupported secure-dirfd platforms, and control-character-bearing paths.

The queue root itself is the nonblocking advisory lock object:

```text
dry-run inspection -> shared LOCK_NB
apply              -> exclusive LOCK_NB
```

A busy lock returns `queue_lock_busy`; B3 does not wait.

The record filename is exactly:

```text
slp-dispatch-v0-<64 lowercase hexadecimal dispatch digest>.json
```

B3 rejects final-record symlinks, non-regular files, link counts other than one, oversized records, and records that change inode during inspection.

## Atomic compare-and-swap replacement

A gated apply uses one same-directory exclusive temporary file:

1. create with `O_CREAT | O_EXCL | O_NOFOLLOW` and private mode,
2. write the complete canonical proposed bytes,
3. `fsync` and verify regular type, size, and single-link evidence,
4. immediately re-open and revalidate the target,
5. require the original device/inode and exact bytes to match the initial snapshot,
6. atomically replace the deterministic target with `rename`/`replace`,
7. `fsync` the queue directory,
8. strictly re-read and compare the committed canonical record and bytes.

A different inode or same-inode byte mutation is a conflict. Corrupt target evidence is never repaired or overwritten. A failure after rename can report `transition_applied=true` with `durability_confirmed=false`, allowing a caller to re-read and converge safely.

## Content-free projection

The public/default projection remains `relaymem.slp_queue_status_projection.v0` and is restricted to:

```text
status
transition kind
queue state
attempt count
claim active
lease present
terminal flag
retry classification
failure classification
transition attempted
transition applied
blocked reason IDs
```

It excludes:

- dispatch idempotency key and job ID,
- run, turn, session, namespace, and lineage values,
- claim owner and lease token,
- exact timestamps,
- queue-root and record paths,
- the durable record body,
- user-visible text, prompts, traces, MEM content, and SOUL content.

The optional `PipelineNodeResult` uses node name `relaymem_slp_queue_state`, marks the runtime-private durable record as omitted, and explicitly reports no worker, MEM, SOUL, or visible-response side effect.

## Preserved non-goals

Phase 6-B3 does not implement:

- scheduler scanning or scheduler loops,
- worker execution or worker heartbeats,
- RelaySLP invocation,
- retry budget calculation or backoff selection,
- request-runtime A1/A2/B1/B2 wiring,
- visible-response dependency or mutation,
- RelayMEM content formation,
- Primary or Secondary MEM apply,
- memory-write idempotency reuse,
- RelaySOUL mutation,
- TTS, audio, Live2D, avatar, or lip-sync control.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_slp_queue_state.py \
  scripts/relaylm_phase6b0_durable_queue_contract_smoke.py \
  scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py \
  scripts/relaylm_phase6b3_queue_state_smoke.py \
  scripts/relaylm_phase6b3_queue_state_security_smoke.py \
  scripts/relaylm_phase6b3_queue_state_contract_smoke.py

PYTHONPATH=. python scripts/relaylm_phase6b0_durable_queue_contract_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_security_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_contract_smoke.py
```

Coverage includes disabled and dry-run gates, all five transitions, active and expired lease boundaries, stale recovery and reclaim monotonicity, all allowed terminal targets, terminal immutability, exact identity/revision/state/owner/generation/token fencing, canonical-record and filesystem corruption, lock contention, timestamp overflow, same-inode byte mutation, content-free projections, and explicit absence of worker/MEM/SOUL/visible-response behavior.

## Next bounded slice

Phase 6-C may execute one claimed job only under the exact active B3 owner, claim-generation, and lease-token fence. It must invoke existing RelayMEM-owned M3a-M3h boundaries without redefining memory meaning, retry policy, or memory-write idempotency, and must preserve visible-response independence.
