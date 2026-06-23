---
relaylm_doc_type: contract
relaylm_authority: phase6c1_primary_mem_worker
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-C1 worker input or outcome schema changes
  - B3 lease or queue transition semantics change
  - RelayMEM M3a-M3h result vocabulary changes
  - protected worker-source persistence changes
  - worker crash-recovery smoke changes
relaylm_not_authoritative_for:
  - RelayMEM memory meaning or page/index/log schemas
  - B3 queue record or transition schemas
  - request-runtime visible-response behavior
  - Secondary MEM consolidation
  - RelaySOUL mutation
  - SOUL Lab TTS audio or avatar execution
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - relaymem_mvp_implementation_plan.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# Phase 6-C1 Primary MEM Worker Contract

## Status

Phase 6-C1 is implemented through C1-5:

```text
C1-0 protected current-claim source
C1-1 RelayMEM M3a-M3h compose
C1-2 one-already-claimed worker
C1-3 pure outcome classifier
C1-4 integrated fault/crash smoke
C1-5 durable protected-source persistence
```

The bounded worker closes the integration boundary between one exact active B3 claim and the existing RelayMEM M3a-M3h primitives. It does not introduce another queue state machine and does not redefine memory semantics.

```text
exact active B3 claim
  + exact protected worker-source bundle
  + configured RelayMEM store root
  -> bounded RelayMEM pipeline composition
  -> lease-fenced retry release or terminal commit
```

The worker executes one already-claimed job only. Queue scanning, generalized scheduling, daemon supervision, worker pools, Secondary MEM, RelaySOUL apply, and SOUL Lab mutation are outside C1.

## Critical source boundary

The canonical B2/B3 durable queue record is intentionally content-free. It contains correlation, namespace, lineage fingerprint, dispatch identity, and queue-control metadata, but it does not contain the governed experience required to create a Primary MEM page.

M3a classifies governed evidence; it is not a content extractor. M3c requires a separately produced governed-experience artifact with bounded trusted title and summary.

A worker must never reconstruct memory content from:

- the durable queue record,
- a B3 public projection,
- generic trace or audit records,
- visible response text recovered from logs,
- frontend metadata or history,
- a public M3 projection,
- a caller-supplied lookalike dictionary.

The exact current-claim source schema is:

```text
relaymem.slp_primary_worker_source.v0
```

C1-0 implements the source bundle. C1-5 implements separate durable claim-independent persistence and restart rehydration.

## Protected worker-source bundle

The bundle is content-bearing and runtime-private. Its exact correlation includes:

```text
schema_version
runtime_private = true
content_included = true
job_id
dispatch_idempotency_key
run_id
turn_index
session_id
namespace
source_event_kind
source_count
source_lineage_fingerprint
relayscn_scene_policy_artifact
relayemo_artifact
governed_messages
governed_experience_artifact
```

It must not be placed in the queue record, `PipelineNodeResult`, generic trace, public error, or default operational projection.

The source producer owns evidence capture and correlation only. RelayMEM owns candidate meaning, summary/page validation, memory-write idempotency, and persistence.

### Live-process compatibility mode

C1-2 may accept an exact in-process source prepared from the optional hot cache. The hot cache is not restart authority.

If neither the hot cache nor the exact durable artifact can supply the protected capture, the job must not execute from queue metadata alone. It fails or blocks under a bounded source-unavailable/corrupt classification.

### Restart-complete protected-source mode

C1-5:

- persists content separately before B2 publishes the queue record,
- binds source schema, job, dispatch, character, and complete capture integrity,
- rejects symlink, path substitution, schema drift, unsafe file type, hardlink, and correlation mismatch,
- retains the artifact through retry release, lease expiry, stale recovery, and a new claim,
- creates a fresh C1-0 source and one-shot scope for each current claim,
- keeps protected content outside generic diagnostics and public APIs,
- removes the artifact only after canonical B3 terminal commit.

This makes protected-source recovery restart-complete for durably enqueued jobs. It does not close a process exit before the post-response background finalizer publishes the source and queue record.

## Exact claimed-record input

C1 consumes one complete canonical `relaymem.slp_durable_job.v0` record with:

```text
state = claimed
claim_owner present
lease_token present
claim_generation >= 1
attempt_count = claim_generation
lease_acquired_at < lease_expires_at
terminal_reason_id empty
retry_not_before null
```

The worker receives the exact current record revision, owner, generation, token, expiry, job identity, and dispatch identity. A public B3 projection is never accepted as a substitute.

## Lease-fencing rules

The worker starts only while the exact claim is active and unexpired.

It revalidates or renews the exact B3 fence:

1. before protected source consumption,
2. before M3e page publication,
3. before M3g index/log apply,
4. before B3 retry release or terminal commit.

The fence is:

```text
job_id
+ dispatch_idempotency_key
+ record_revision
+ state = claimed
+ claim_owner
+ claim_generation
+ lease_token
+ unexpired lease
```

A successful renewal increments record revision. The worker replaces its expected record with the renewed canonical record before continuing.

On lease loss, expiry, stale recovery conflict, revision conflict, owner mismatch, generation mismatch, or token mismatch:

- no new side effect begins,
- success is not claimed,
- no stale retry/terminal transition is attempted,
- a later exact claim may converge through both idempotency domains.

An already completed durable side effect is not rolled back.

## RelayMEM composition boundary

C1-2 calls the RelayMEM-owned:

```python
execute_relaymem_primary_pipeline(...)
```

Canonical order:

```text
M3a formation candidate
  -> M3b source lineage and write preflight
  -> M3c deterministic page candidate
  -> M3d writer handoff
  -> M3e atomic page publication
  -> M3f reconciliation plan
  -> M3g index-before-log apply
  -> M3h read-only recovery audit
```

Every direct-helper validator still executes. Compose reduces orchestration mistakes; it does not weaken defense in depth.

The compose ledger is runtime-private. Public projection exposes only bounded stage/status/boolean/count/reason fields.

## Idempotency domains

Two domains remain separate.

### Dispatch idempotency

```text
dispatch_idempotency_key
  owned by Phase 6 / RelayRUN
  prevents duplicate logical queue dispatch and active execution scheduling
```

### Memory-write idempotency

```text
memory-write idempotency key
  produced and owned by RelayMEM M3b
  propagated through M3c-M3h
  prevents duplicate durable page/index/log application
```

The worker never derives one key from the other, copies dispatch identity into memory-write fields, accepts a memory-write key as queue identity, or exposes either key publicly.

A new claim reruns the deterministic RelayMEM chain from a fresh exact protected source. M3e/M3g converge through memory-write idempotency while B3 fences execution through dispatch identity.

## M3f plan lifetime

Within one active claim, an exact runtime-private M3f plan may be retained for immediate M3g use.

Across process restart or a new claim, the worker regenerates a fresh M3f plan from current durable state. The plan is never serialized into the content-free queue record.

## Outcome classification

Phase 6 owns queue control. RelayMEM owns the meaning of stage results. C1-3 maps exact RelayMEM evidence to existing B3 transitions.

### Terminal success

Commit `succeeded` only when:

- M3e page state is exact or idempotently exact,
- M3g is `applied` or `already_applied`,
- M3h is `recovery_not_required`,
- the final B3 lease fence remains exact and active.

```text
terminal_state = succeeded
failure_class = none
terminal_reason_id = primary_mem_durable_state_verified
```

### Transient resource contention

M3g exclusive-lock contention, M3h audit-lock contention, and bounded queue/source-store lock contention with no mutation map to:

```text
retry_release
retry_class = transient_lock_contention
failure_class = resource_contention
```

### Safe reconciliation retry

Verified `index_applied_log_pending` with `retry_reconciliation` maps to:

```text
retry_release
retry_class = primary_reconciliation_retry
failure_class = partial_progress_verified
```

A new claim regenerates M3f from current state.

### Policy held or blocked

Current B3 has no `held` queue state. Exact RelayMEM policy evidence commits terminal failed with bounded `memory_policy_held` or `memory_policy_blocked`. Memory meaning remains in the protected RelayMEM domain.

### Manual confirmation and recovery isolation

`manual_confirmation_required` and `journaled_recovery_candidate` are terminal failed classifications. C1 never invents unsupported `dead_letter` generation and never automatically repairs uncertain state.

### Store conflict, corruption, or divergence

Page missing/digest mismatch, malformed/conflicting control state, invalid store evidence, source correlation mismatch, `state_diverged`, `page_unverified`, and `control_unverified` never produce success and are not blindly retried.

If the lease is already lost, the stale worker stops without terminal commit.

### Durability uncertainty

M3e/M3g durability uncertainty must pass through M3h. Uncertainty is never collapsed into success.

## Retry policy bounds

The implemented C1-2 worker supports only:

- transient lock contention,
- verified reconciliation partial progress,
- lease renewal/reclaim coordination.

It includes finite attempt limits, bounded deterministic jitter/backoff, no infinite immediate retry, and no automatic retry for corruption, policy hold, manual confirmation, or recovery isolation.

B3 stores retry metadata but does not calculate policy.

## M3g/M3h concurrency

M3g serializes `memory/mem/index.md` and `memory/mem/log.md` updates with one nonblocking exclusive directory lock. M3h shared audit may contend with an active writer.

Lock contention is a normal retryable operational outcome when no invalid store evidence exists. Workers release and back off; they do not spin.

## Crash and restart behavior

Integrated smoke covers:

1. after claim and before source consumption,
2. after M3e and before M3f,
3. after index publication and before log publication,
4. after full reconciliation and before B3 terminal commit,
5. lease expiry while another worker performs stale recovery.

Rules:

- visible response state never changes,
- stale recovery may return work to queued,
- a new claim rehydrates a fresh source through C1-5,
- M3e recognizes an exact existing page,
- M3f derives current state,
- M3g recognizes exact or verified partial progress,
- M3h decides success/retry/manual/isolation evidence,
- only the current lease holder transitions queue state.

If the exact durable source is missing or corrupt after restart, execution fails closed; queue metadata is never used to reconstruct content.

## Required smoke matrix

C1 coverage includes:

- exact claim/source correlation,
- normal M3a-M3h success and B3 terminal success,
- duplicate dispatch behavior,
- same-memory idempotent rerun,
- M3e crash and new-claim convergence,
- index-before-log crash and reconciliation convergence,
- M3g/M3h lock contention and bounded retry release,
- lease renewal before M3e/M3g,
- lease loss before/after side effect,
- stale generation/token rejection,
- policy held/blocked terminal classification,
- manual-confirmation/recovery-isolation behavior,
- restart rehydration and missing/corrupt source isolation,
- wrong character/namespace/run/turn/lineage/job/dispatch rejection,
- no protected content, paths, keys, tokens, timestamps, or memory body in public diagnostics.

Next-turn retrieval/RelayCTX injection is an I1 integration smoke, not a C1 worker prerequisite.

## Public projection

May expose:

```text
schema/status
current stage and counts
retryable/terminal booleans
policy-held/manual/recovery booleans
lease-valid/renewed booleans
source-present/correlation-valid booleans
page/index/log/recovery booleans
bounded retry/failure/terminal reason IDs
```

Must not expose raw messages, visible response text, governed title/summary, page/index/log content, source body, paths, namespace, runtime identities, lineage, idempotency keys, lease material, timestamps, or OS exception text.

## Preserved non-goals

C1 does not:

- perform request-runtime enqueue itself,
- scan the queue or implement a scheduler loop,
- create a generalized worker pool,
- weaken M3 validators,
- redefine memory meaning or safety policy,
- place protected source content in the queue,
- implement Secondary MEM,
- directly mutate RelaySOUL,
- expose Lab mutation,
- execute TTS/audio/Live2D/avatar behavior,
- make visible-response success depend on deferred work.

## Implementation sequence

```text
C1-0 protected worker source                    complete
C1-1 M3a-M3h compose                            complete
C1-2 one already-claimed worker                 complete
C1-3 outcome mapping                            complete
C1-4 crash/lease/lock/fault smoke               complete
C1-5 restart-complete protected source recovery complete for durably enqueued jobs
```

The next boundary is a thin one-job queued-record claim/rehydrate/execute adapter, followed by next-turn recall. I1 separately retains the pre-enqueue background-finalizer crash window.
