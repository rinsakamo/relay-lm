---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_durable_protected_source_persistence
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - protected worker-source artifact schema or integrity binding changes
  - I1-B source publication order changes
  - claim-time rehydration or terminal cleanup ownership changes
relaylm_not_authoritative_for:
  - RelaySLP queue-record schema or B3 lifecycle semantics
  - worker retry timing or attempt limits
  - RelayMEM M3a-M3h formation and persistence semantics
  - queue scanning, scheduling, daemon, or service lifecycle
  - next-turn retrieval, RelayCTX injection, or SOUL Lab observation
relaylm_related_authority:
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c2_one_queued_primary_worker_integration.md
  - i1g_pre_enqueue_durable_finalization_contract.md
---
# Phase 6-C1-5 Durable Protected Source Persistence

## Status

Phase 6-C1-5 makes protected worker-source recovery restart-complete for durably enqueued jobs without adding source content to the RelaySLP queue record.

```text
exact finalized-turn capture
  -> durable protected-source commit
  -> canonical B2 content-free enqueue
  -> optional process-local hot cache

current exact B3 claim
  -> hot-cache or durable lookup
  -> identity and integrity validation
  -> fresh C1-0 scope and source
  -> C1-2 one-claimed worker
```

This closes the post-enqueue source-recovery boundary. It does not implement queue scanning, scheduling, daemon lifecycle, next-turn recall, SOUL Lab observation, or recovery of a turn that never reached background source/queue publication.

## Ownership

- I1-B owns finalized-turn content production and canonical B1 identity construction.
- C1-5 owns protected capture persistence, validation, restart lookup, and post-terminal cleanup.
- B2 owns content-free queue publication.
- B3 owns claim, lease, retry release, stale recovery, and terminal queue state.
- C1-0 owns current-claim correlation and one-shot source construction.
- C1-2 owns one current claimed-job execution and retry timing.
- M3a-M3h own Primary MEM formation and persistence.

No queue-record field or B2/B3 state meaning changes in this slice.

## Durable artifact

The runtime-private schema is:

```text
relaymem.slp_protected_source_artifact.v0
```

Top-level fields:

```text
schema_version
runtime_private
content_included
source_schema_version
job_id
dispatch_idempotency_key
character_id
source_integrity_digest
protected_capture
```

`protected_capture` is the exact claim-independent C1-0 payload produced by I1-B. The integrity digest binds source schema, queue identities, character identity, and complete protected capture under canonical serialization.

Claim owner/token, lease timestamps, generation, revision, and a previous one-shot scope are not stored.

## Publication and recovery

Publication order is fixed:

```text
canonical I1-B preparation
  -> protected source durable commit
  -> canonical B2 enqueue
  -> optional hot-cache publication
```

An equivalent existing artifact is idempotent. Same identity with different protected content is rejected and never overwritten.

Crash convergence:

| Point | Result |
|---|---|
| before source publication | no queue record and no source artifact |
| after source, before enqueue | complete orphan; exact repeat may continue idempotently |
| after enqueue | committed source is available for restart lookup |
| before terminal transition | source remains available for retry/new claim |
| after terminal transition, before cleanup | queue terminal state remains authoritative |

The source-before-queue order prevents a durably enqueued record from lacking its committed source artifact.

When B2 success is not observed, C1-5 distinguishes two cases:

- if the queue root itself is still absent, queue publication is impossible and a newly created artifact may be removed synchronously;
- for every other uncertain outcome, including a possible late fsync or verification failure after queue publication, the complete artifact is retained and reported as `cleanup_required` with `protected_source_orphan_reconciliation_required`.

This intentionally prefers a complete orphan over a claimable queue record whose protected source was deleted. This slice does not add the future reconciliation or cleanup scanner.

The separate unresolved window is:

```text
visible response delivered
  -> process exits before the background finalizer publishes source and queue
```

C1-5 cannot rehydrate an artifact that was never published.

## I1-GA / I1-GB alignment

[I1-G Pre-enqueue Durable-finalization Contract and Fault Model](i1g_pre_enqueue_durable_finalization_contract.md) defines the turn-scoped sealed record before this C1-5 boundary. I1-GB implements only pre-release base/segment/seal publication and leaves this C1-5 artifact schema, publication semantics, cleanup ownership, and source-before-queue order unchanged. I1-GC restart replay/completion convergence, I1-GD cleanup, and I1-GE full crash validation remain unimplemented.

## Retry and stale recovery

Retry release, lease expiry, and stale recovery retain the durable artifact. Each new claim creates a fresh C1-0 source object and one-shot scope from the same claim-independent capture.

A stale or consumed source object remains invalid. C1-5 does not calculate retry delay, jitter, or attempt limits.

## Terminal cleanup

Cleanup begins only after canonical B3 terminal commit. It releases hot-cache state and removes the matching durable artifact.

Cleanup failure returns bounded cleanup-required state and never rolls back the queue transition. This slice adds no background cleanup service.

## Public boundary

Public projections and workflow diagnostics expose only bounded status and reason fields. They omit protected content, paths, identities, digests, namespace/lineage values, and exception detail.

## Configuration

Apply mode additionally requires:

```yaml
relaymem_slp_protected_source_root: /absolute/runtime-private/path
relaymem_slp_protected_source_max_artifact_bytes: 262144
```

The root must already exist and be protected by deployment permissions. Dry-run remains usable without it.

## Verification

Dedicated smoke covers:

- create/read/restart rehydration and idempotent duplicate handling,
- malformed or mismatched artifact rejection,
- bounded storage and safe file handling,
- source-before-queue ordering, provable no-enqueue cleanup, and uncertain-outcome artifact retention,
- retry release, new generation, fresh source/scope, and terminal convergence,
- post-terminal cleanup behavior,
- separate-process producer/restart-consumer execution through C1-2,
- content-free queue, projection, repr, filename, stdout, and stderr surfaces,
- C1-0, I1-B, B2, B3, C1-2, C1-4, documentation, onboarding, RelayCTX, and TTS regressions.

## Accurate completion boundary

> Phase 6-C1 is restart-complete for protected worker-source recovery of durably enqueued jobs. Phase I-1 next-turn recall, Phase I-2 observation, Phase I-3 Correct, UI-B0 real Home conversation, and C2 are complete through their separate authorities. I1-GB now preserves sealed evidence before protected response release; restart replay and completion convergence remain I1-GC work.
