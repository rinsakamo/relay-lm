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
  - RT-1 Primary writer-decision carriage or admission changes
  - RT-1D-R5 or R6 retires the Primary worker path
relaylm_not_authoritative_for:
  - RelaySLP queue-record schema or B3 lifecycle semantics
  - worker retry timing or attempt limits
  - RelayMEM M3a-M3h formation and persistence semantics
  - queue scanning, scheduling, daemon, or service lifecycle
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - next-turn retrieval, RelayCTX injection, or SOUL Lab observation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c2_one_queued_primary_worker_integration.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../PROJECT_STATUS.md
---
# Phase 6-C1-5 Durable Protected Source Persistence

Last reviewed: 2026-08-08 JST

## Status

Phase 6-C1-5 makes protected worker-source recovery restart-complete for durably enqueued jobs without adding source content to the RelaySLP queue record.

Under current RT-1D-R4 semantics, this is durable work/evidence availability for the retained Primary compatibility worker. It is not durable Primary writer authorization. Every later C2/C1-2/C1-1 execution still requires the exact caller-carried Primary writer decision owned by the cutover domain.

```text
exact finalized-turn capture
  -> durable protected-source commit
  -> canonical B2 content-free enqueue
  -> optional process-local hot cache

current exact B3 claim
  + exact RT-1 Primary writer decision
  -> rejected decision: no Primary worker execution authority
  -> permitted decision:
       hot-cache or durable lookup
       -> identity and integrity validation
       -> fresh C1-0 scope and source
       -> C1-2 one-claimed worker
```

This closes the post-enqueue source-recovery boundary. It does not implement queue scanning, scheduling, daemon lifecycle, next-turn recall, SOUL Lab observation, recovery of a turn that never reached background source/queue publication, or RT-1 writer authorization.

## Writer-authorization boundary

C1-5 owns persistence and rehydration only. A valid durable artifact, valid queue record, current claim, retained retry, or exact idempotent source state cannot mint or preserve a `permitted` writer decision.

The current execution hierarchy checks authorization separately:

```text
C2 enabled one-job runner
  -> writer decision must permit before B3 claim/source/worker execution

C1-2 one-claimed worker
  -> writer decision must permit before active-claim/source/pipeline execution

C1-1 Primary pipeline
  -> writer decision must permit before mode gates/source consumption/M3a-M3h
```

C1-5 does not resolve, cache, refresh, serialize, or reconstruct `SubjectiveMemRetrievalPrimaryWriterDecision`. Writer-decision identity is not part of the protected-source artifact. This separation ensures that crash recovery can preserve evidence without reviving a Primary writer after the owning cutover boundary has fenced it.

## Ownership

- I1-B owns finalized-turn content production and canonical B1 identity construction.
- C1-5 owns protected capture persistence, validation, restart lookup, and post-terminal cleanup.
- B2 owns content-free queue publication.
- B3 owns claim, lease, retry release, stale recovery, and terminal queue state.
- C1-0 owns current-claim correlation and one-shot source construction.
- C1-2 owns one current claimed-job execution and retry timing after its writer-decision admission gate.
- M3a-M3h own Primary MEM formation and persistence after pipeline admission.
- RT-1 cutover authority owns whether a Primary writer decision is `permitted` or `rejected`.

No queue-record field or B2/B3 state meaning changes in this slice. Queue/source ownership and writer authorization remain separate domains.

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

Claim owner/token, lease timestamps, generation, revision, a previous one-shot scope, and RT-1 writer-decision identity are not stored.

The absence of writer authorization from the artifact is intentional. Integrity says that the protected evidence is exact; it does not say that Primary mutation is currently authorized.

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

Retaining a complete orphan or a claimable queue/source pair preserves evidence and recovery options only. Neither state authorizes execution when the caller-carried RT-1 writer decision is rejected.

The separate unresolved window is:

```text
visible response delivered
  -> process exits before the background finalizer publishes source and queue
```

C1-5 cannot rehydrate an artifact that was never published.

## I1-GA / I1-GB alignment

[I1-G Pre-enqueue Durable-finalization Contract and Fault Model](i1g_pre_enqueue_durable_finalization_contract.md) defines the turn-scoped sealed record before this C1-5 boundary. I1-GB implements only pre-release base/segment/seal publication and leaves this C1-5 artifact schema, publication semantics, cleanup ownership, and source-before-queue order unchanged. I1-GC restart replay/completion convergence, I1-GD cleanup, and I1-GE full crash validation remain unimplemented.

The I1-G status in this section is preserved as its own authority boundary. The RT-1 writer-fence clarification in this handoff does not modify I1-G sequencing or completion claims.

## Retry and stale recovery

Retry release, lease expiry, and stale recovery retain the durable artifact. Each new claim creates a fresh C1-0 source object and one-shot scope from the same claim-independent capture.

A stale or consumed source object remains invalid. C1-5 does not calculate retry delay, jitter, or attempt limits.

A later claim or retry must still carry an exact writer decision accepted by the C2/C1-2/C1-1 execution gates. Retry availability is not writer permission, and stale recovery cannot restore Primary writer authority after `primary_writer_fenced`.

## Terminal cleanup

Cleanup begins only after canonical B3 terminal commit. It releases hot-cache state and removes the matching durable artifact.

Cleanup failure returns bounded cleanup-required state and never rolls back the queue transition. This slice adds no background cleanup service.

Terminal or cleanup state does not participate in RT-1 writer authorization.

## Public boundary

Public projections and workflow diagnostics expose only bounded status and reason fields. They omit protected content, paths, identities, digests, namespace/lineage values, private writer-decision identity, and exception detail.

## Configuration

Apply mode additionally requires:

```yaml
relaymem_slp_protected_source_root: /absolute/runtime-private/path
relaymem_slp_protected_source_max_artifact_bytes: 262144
```

The root must already exist and be protected by deployment permissions. Dry-run remains usable without it.

Configuration of a protected-source root enables storage mechanics only; it does not grant Primary writer permission.

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

The broader C2/C1 worker regression set separately verifies that a foreign/non-permitted writer decision fails closed before claim/source/worker or pipeline execution. C1-5's dedicated persistence tests remain evidence/storage tests rather than writer-authority tests.

## Accurate completion boundary

> Phase 6-C1 is restart-complete for protected worker-source recovery of durably enqueued jobs. Phase I-1 next-turn recall, Phase I-2 observation, Phase I-3 Correct, UI-B0 real Home conversation, and C2 are complete through their separate authorities. I1-GB now preserves sealed evidence before protected response release; restart replay and completion convergence remain I1-GC work.

This completion boundary describes implemented storage/recovery capability. It does not preserve independent Primary writer authority after the owning RT-1 cutover decision rejects that writer class. R5/R6 own final retirement or explicitly retained historical/read-only/test disposition of the Primary worker/source surfaces after exact dependency characterization.
