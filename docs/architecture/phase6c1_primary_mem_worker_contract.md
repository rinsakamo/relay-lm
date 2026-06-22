---
relaylm_doc_type: implementation_contract
relaylm_authority: phase6c1_primary_mem_worker
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-C1 worker input or outcome schema changes
  - B3 lease or queue transition semantics change
  - RelayMEM M3a-M3h result vocabulary changes
  - protected worker-source persistence lands
  - worker implementation or crash-recovery smoke lands
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
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_execution_design.md
  - relaymem_m3a_primary_formation_handoff.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# Phase 6-C1 Primary MEM Worker Contract

## Status

This document defines the first bounded Phase 6-C1 worker contract. The worker implementation is pending.

The contract closes the integration boundary between an exact active B3 claim and the existing RelayMEM M3a-M3h primitives. It does not introduce another queue-helper phase and does not redefine memory semantics.

```text
exact active B3 claim
  + exact protected worker-source bundle
  + configured RelayMEM store root
  -> bounded RelayMEM pipeline composition
  -> lease-fenced retry release or terminal commit
```

The first implementation executes one already-claimed job. Scheduler scanning, generalized worker pools, process supervision, Secondary MEM, RelaySOUL apply, and SOUL Lab mutation are outside this slice.

## Critical source boundary

The canonical B2/B3 durable queue record is intentionally content-free. It contains correlation, namespace, lineage fingerprint, dispatch identity, and queue-control metadata, but it does not contain the governed experience body required to create a Primary MEM page.

M3a classifies whether governed evidence may produce a Primary MEM candidate. It is not a content extractor. M3c requires a separately produced governed-experience artifact containing a bounded trusted title and summary.

Therefore a worker must not attempt to reconstruct memory content from:

- the durable queue record,
- the B3 public projection,
- generic trace or audit records,
- visible response text recovered from logs,
- frontend metadata,
- a public M3 projection,
- a caller-supplied lookalike dictionary.

The required protected input is an exact runtime-private source bundle:

```text
relaymem.slp_primary_worker_source.v0
```

Its implementation and persistence boundary are prerequisites for C1 execution.

## Protected worker-source bundle

The bundle is content-bearing and belongs to the protected memory/source domain. It must contain exact correlation with the claimed job:

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

The bundle must not be placed in the B2/B3 queue record, `PipelineNodeResult`, generic trace, public error, or default operational projection.

The source bundle producer owns only protected evidence capture and exact correlation. RelayMEM continues to own candidate meaning, summary/page validation, memory-write idempotency, and persistence.

### Initial live-source mode

The first bounded worker may accept an exact in-process source bundle retained by request-runtime C0 wiring. This mode is sufficient for a first live-process integration smoke but is not restart-complete.

If the process restarts and the exact protected source bundle is unavailable, the job must not execute from queue metadata alone. It remains queued/failed under an explicit bounded source-unavailable classification; raw content must not be reconstructed from traces or UI history.

### Restart-complete mode

I1 restart completion requires one protected durable source-artifact design or another exact rehydratable source owner. That design must:

- persist content separately from the content-free queue record,
- bind the artifact to dispatch/job/run/turn/session/namespace/lineage identity,
- reject symlink, path substitution, schema drift, and correlation mismatch,
- use explicit retention and deletion rules,
- remain inaccessible to generic trace and public APIs,
- permit a new claim to rerun the deterministic RelayMEM chain.

A durable protected source artifact is not optional for crash recovery before M3e when the original process-local evidence is gone.

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

The worker receives the exact current:

- record revision,
- claim owner,
- claim generation,
- lease token,
- lease expiry,
- job and dispatch identities.

The worker must not consume a public B3 projection as a substitute for the runtime-private claimed record.

## Lease-fencing rules

The worker may start only while the exact claim is active and unexpired.

It must revalidate or renew the exact B3 fence at these checkpoints:

1. before protected source consumption,
2. before M3e page publication,
3. before M3g index/log apply,
4. before any B3 retry-release or terminal commit.

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

A successful B3 renewal increments record revision. The worker must replace its expected revision with the renewed canonical record before continuing.

On lease loss, expiry, stale-recovery conflict, revision conflict, owner mismatch, generation mismatch, or token mismatch:

- do not begin another side effect,
- do not claim success,
- do not commit a terminal queue state with a stale fence,
- allow a later exact claim to converge through dispatch and memory-write idempotency.

An operation already completed before lease loss is not rolled back. A later worker must rediscover it through the existing idempotent RelayMEM boundaries.

## RelayMEM composition boundary

The worker should call one RelayMEM-owned composition function, provisionally:

```python
execute_relaymem_primary_pipeline(...)
```

The compose function fixes stage order and exact artifact handoff while preserving direct access to each existing M3 helper for tests, audit, and future recovery work.

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

The compose function must not weaken or bypass the exact validators in any stage. Its purpose is to reduce orchestration mistakes, not to remove defense in depth.

The compose result should provide one runtime-private stage ledger and one content-free projection. The ledger may retain exact private artifacts needed within the active claim. The public projection may expose only stage names, bounded statuses, booleans, counts, and reason IDs.

## Idempotency domains

Two idempotency domains remain separate.

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

The worker may correlate the two domains in a private execution ledger, but it must never:

- derive one key from the other,
- copy the dispatch key into an M3 memory-write field,
- accept a memory-write key as a queue identity,
- expose either key in public projections.

A new claim after a crash reruns the RelayMEM chain from the exact protected source bundle. M3e and M3g then converge through memory-write idempotency while B3 continues to fence queue ownership through dispatch identity.

## M3f plan lifetime

Within one active claim, the worker may retain the exact runtime-private M3f plan in memory and use it for an immediate M3g retry.

Across process restart or a new claim, the worker must not depend on an in-memory plan. It reruns the deterministic chain and generates a fresh M3f plan from current durable state.

The M3g receipt alone cannot drive reconciliation because it does not contain proposed control-file content. C1 must not serialize the M3f plan into the content-free queue record.

## Outcome classification

Phase 6 owns queue control. RelayMEM owns the meaning of each result. C1 maps exact RelayMEM outcomes to existing B3 transitions without changing their semantics.

### Terminal success

Commit `succeeded` only when:

- M3e page state is exact or idempotently exact,
- M3g reports `applied` or `already_applied`,
- M3h reports `recovery_not_required`,
- the final B3 lease fence is still exact and active.

Suggested queue metadata:

```text
terminal_state = succeeded
failure_class = none
terminal_reason_id = primary_mem_durable_state_verified
```

### Transient resource contention

The following are expected transient operational outcomes, not corruption or policy failure:

- M3g `primary_reconciliation_apply_lock_unavailable`,
- M3h read-audit lock contention,
- a bounded queue/source-store lock contention where no mutation occurred.

Map them to B3 `retry_release` with a short bounded backoff and jitter:

```text
retry_class = transient_lock_contention
failure_class = resource_contention
```

Retry count remains bounded by worker policy. B3 records the chosen classification and timestamp but does not calculate policy.

### Safe reconciliation retry

When M3g/M3h verifies:

```text
index_applied_log_pending
+ recovery_classification = retry_reconciliation
```

map to B3 `retry_release`:

```text
retry_class = primary_reconciliation_retry
failure_class = partial_progress_verified
```

Within the same live claim, the exact retained M3f plan may be reused. On a new claim, rerun M3a-M3f and generate a current plan.

### Policy-held or policy-blocked memory

A RelayMEM policy outcome is terminal for the queue execution attempt. It is not a queue corruption state.

Because the current B3 state machine has no `held` queue state, use:

```text
terminal_state = failed
failure_class = memory_policy_held | memory_policy_blocked
terminal_reason_id = bounded RelayMEM policy reason
```

The held/blocked memory meaning remains in the protected RelayMEM domain and may later be exposed through a Lab-owned memory outcome API.

### Manual confirmation

M3h `manual_confirmation_required` must not trigger automatic page/index/log reapply.

Map to:

```text
terminal_state = failed
failure_class = manual_confirmation_required
terminal_reason_id = primary_mem_manual_confirmation_required
```

### Journal-aware recovery candidate

M3h `journaled_recovery_candidate` does not authorize repair. Current B3 cannot generate `dead_letter`; therefore C1 terminates as:

```text
terminal_state = failed
failure_class = recovery_isolation_required
terminal_reason_id = primary_mem_journaled_recovery_candidate
```

A later explicit isolation policy may introduce dead-letter generation. C1 must not invent one through an unsupported transition.

### Store conflict, corruption, or divergence

Examples include:

- page missing or digest mismatch after a claimed write path,
- index/log conflict not classified as verified partial progress,
- invalid/corrupt canonical store evidence,
- `state_diverged`, `page_unverified`, or `control_unverified`,
- source-bundle correlation mismatch.

Do not retry blindly. Commit `failed` when the current lease is still valid:

```text
failure_class = store_conflict | store_corruption | source_correlation_invalid
```

If the lease is already lost, stop without a stale terminal commit and let the current claimant classify the state.

### Durability uncertainty

`applied_durability_unconfirmed`, `applied_cleanup_incomplete`, or `applied_state_uncertain` must pass through M3h before queue classification.

- fully reconciled but durability unconfirmed -> `manual_confirmation_required`,
- verified `index_applied_log_pending` -> bounded reconciliation retry,
- uncertain/diverged/cleanup-sensitive state -> recovery isolation required,
- never collapse uncertainty into success.

## Retry policy bounds

C1 owns a small, explicit policy table. B3 remains a storage/transition helper.

The first worker implementation should support only:

- transient lock contention,
- verified reconciliation partial progress,
- lease renewal/reclaim coordination.

It must include:

- finite attempt limits,
- bounded backoff,
- jitter for shared M3g lock contention,
- no automatic retry for corruption, policy hold, manual confirmation, or journal candidate,
- no infinite immediate retry loop.

Exact durations and attempt limits belong in code/config and smoke tests, not duplicated across architecture documents.

## M3g/M3h concurrency model

Multiple B3 claims may execute concurrently for distinct jobs, but M3g serializes all `memory/mem/index.md` and `memory/mem/log.md` updates under one non-blocking exclusive directory lock.

Therefore:

- page formation/publication may proceed concurrently where existing M3 contracts permit,
- index/log reconciliation is an intentional single-writer critical section,
- lock failure is normal transient contention,
- workers must release and back off rather than spin,
- M3h shared audit may also contend with an active M3g writer and is retryable when no invalid store evidence exists.

The first worker implementation does not need a broad pool. One bounded worker is sufficient for the first end-to-end proof; concurrency smoke still must prove that a second worker cannot corrupt or duplicate durable state.

## Crash and restart behavior

Required crash points:

1. after claim and before source consumption,
2. after M3e page publication and before M3f,
3. after M3g index publication and before log publication,
4. after fully reconciled memory and before B3 terminal commit,
5. during lease expiry while another worker performs stale recovery.

Rules:

- a crash never changes an already finalized visible response,
- stale recovery may return the job to `queued`,
- a new claim reruns from the exact protected source bundle,
- M3e recognizes an exact existing page as idempotent,
- M3f derives a plan from current state,
- M3g recognizes exact proposed control state and verified partial progress,
- M3h decides whether success, retry, manual confirmation, or isolation is safe,
- only the current lease holder may release or commit queue state.

If the durable protected source artifact is absent after restart, the job cannot safely rerun the full chain. This must be an explicit source-unavailable result, not silent loss or trace-based reconstruction.

## Required smoke matrix

The C1 implementation is incomplete until smoke covers:

1. exact claimed-record and source-bundle correlation,
2. normal M3a-M3h success and B3 terminal success,
3. same dispatch replay with no second queue record,
4. rerun with the same protected source producing the same memory-write identity,
5. M3e success followed by worker crash and new-claim convergence,
6. M3g index-success/log-pending crash and new-claim convergence,
7. M3g exclusive-lock contention -> bounded retry release,
8. M3h shared-lock contention -> bounded retry release,
9. lease renewal before M3e and M3g,
10. lease loss before side effect -> no further side effect,
11. lease loss after side effect -> no stale terminal commit and later idempotent convergence,
12. parallel worker attempting the same stale generation/token -> fenced rejection,
13. policy-held and policy-blocked outcomes -> failed classification without memory apply,
14. manual confirmation and journal candidate -> no automatic retry/apply,
15. source-bundle unavailable after restart -> explicit safe block,
16. wrong character, namespace, run, turn, lineage, job, or dispatch correlation -> fail closed,
17. no protected content, paths, keys, tokens, timestamps, or memory body in public diagnostics,
18. next-turn retrieval and RelayCTX injection only after verified durable success.

## Content-free public projection

The worker public projection may expose:

```text
schema version
status
current stage
stage count
completed stage count
retryable boolean
terminal boolean
policy-held boolean
lease-valid boolean
lease-renewed boolean
source-bundle-present boolean
source-correlation-valid boolean
page verified/applied booleans
index/log reconciled booleans
recovery classification enum
bounded retry/failure/terminal reason IDs
```

It must not expose:

- raw messages or visible response text,
- governed title or summary,
- page/index/log content,
- source artifact body,
- queue/store paths,
- namespace values,
- run/session/job/dispatch identifiers,
- lineage fingerprints,
- memory-write idempotency keys,
- claim owner, lease token, or exact timestamps,
- OS exception strings.

## Preserved non-goals

Phase 6-C1 does not:

- perform request-runtime enqueue wiring itself,
- scan the queue or implement a scheduler loop,
- create a generalized worker pool,
- weaken M3 validators,
- redefine memory meaning or safety policy,
- persist protected source content in the content-free queue record,
- implement Secondary MEM,
- directly mutate RelaySOUL,
- expose memory mutation through SOUL Lab,
- execute TTS, audio, Live2D, avatar, or lip-sync behavior,
- make visible-response success depend on deferred work.

## Implementation sequence

```text
C1-0 protected worker-source bundle contract and exact correlation
C1-1 RelayMEM M3a-M3h compose function
C1-2 one already-claimed B3 worker execution
C1-3 outcome mapping and B3 retry/terminal transitions
C1-4 crash, lease-loss, and lock-contention smoke
C1-5 restart-complete protected source persistence
```

C1-0 through C1-4 may prove the live-process loop. I1 restart completion additionally requires C1-5 or an equivalent exact durable source owner.
