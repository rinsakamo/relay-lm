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
---
# Phase 6-C1-5 Durable Protected Source Persistence

## Status

Phase 6-C1-5 makes the protected worker-source recovery boundary restart-complete without adding source content to the RelaySLP queue record.

The implemented production chain is:

```text
exact finalized-turn capture
  -> canonical I1-B dry-run identity and source payload construction
  -> durable protected-source create-if-absent commit
  -> unchanged canonical B2 content-free durable enqueue
  -> optional process-local registry hot cache

current exact B3 claimed record
  -> process-local hot-cache lookup or durable artifact lookup
  -> schema / identity / integrity validation
  -> fresh C1-0 one-shot scope
  -> canonical C1-0 builder
  -> fresh unconsumed worker source
  -> C1-2 one-claimed worker
```

This closes restart recovery of the protected worker source. It does not implement a queue scanner, scheduler, daemon, next-turn recall, or SOUL Lab observation.

## Ownership

- I1-B owns finalized-turn content production and canonical B1 identity construction.
- C1-5 owns protected capture persistence, validation, restart lookup, and post-terminal cleanup.
- B2 remains the sole owner of content-free durable queue publication.
- B3 remains the sole owner of claim, lease, retry release, stale recovery, and terminal queue state.
- C1-0 remains the sole owner of current-claim source correlation and one-shot source construction.
- C1-2 remains the sole owner of one current claimed-job execution and retry timing.
- M3a-M3h remain the sole owners of Primary MEM formation and persistence.

No queue-record field or B2/B3 state-machine meaning changes in this slice.

## Durable artifact

The runtime-private artifact schema is:

```text
relaymem.slp_protected_source_artifact.v0
```

Its exact top-level fields are:

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

`protected_capture` is the exact claim-independent 16-field C1-0 payload produced by I1-B. The integrity digest binds source schema version, queue job identity, dispatch identity, character identity, and the complete protected capture under canonical JSON serialization.

Claim token, claim owner, lease timestamps, claim generation, record revision, and a prior one-shot scope are not stored in the artifact.

The deterministic artifact filename is derived only from the artifact schema and canonical queue identities. It does not include message text, namespace text, lineage text, source content, or raw digest input.

## Filesystem contract

The store requires an absolute pre-existing runtime-private root and uses secure directory-FD traversal. It rejects parent traversal, symlink roots, non-directory roots, changed directory inodes, symlink artifacts, non-regular artifacts, hard-linked artifacts, oversized artifacts, malformed UTF-8, malformed JSON, duplicate JSON keys, non-canonical serialization, unsupported schemas, unexpected or missing fields, identity mismatch, and integrity mismatch.

Publication uses:

```text
exclusive random 0600 temporary file
  -> bounded full write
  -> file fsync
  -> Linux renameat2(RENAME_NOREPLACE)
  -> directory fsync
  -> exact published-byte verification
```

An equivalent existing artifact is idempotent. The same queue identity with different protected content is a collision and is never overwritten. Temporary files are never accepted by claim-time lookup.

## Publication order and crash convergence

The production adapter fixes publication order as follows:

```text
canonical I1-B dry-run preparation
  -> protected source durable commit
  -> canonical I1-B apply / B2 enqueue
  -> process-local hot-cache publication
```

Crash windows converge as follows:

| Crash point | Result |
|---|---|
| before source write | no queue record and no source artifact |
| after temporary write, before publish | unpublished temporary file is ignored |
| after source commit, before enqueue | complete orphan; an exact repeat is idempotent and can continue to B2 |
| after enqueue | queue record always has a committed source artifact available for restart lookup |
| after queue publish, before hot-cache publication | restart lookup uses the durable artifact; hot-cache loss is non-fatal |
| before terminal transition | artifact remains available for retry or new claim |
| after terminal transition, before cleanup | terminal queue state is preserved; cleanup helper removes the artifact or emits cleanup-required state |

When B2 fails synchronously after this call created a new source artifact, the adapter validates and removes that exact orphan. A process crash can leave a complete orphan, but never a claimable queue record without a committed source artifact.

## Retry and stale recovery

`retry_release`, lease expiry, and stale recovery do not remove the durable artifact. Generation N and generation N+1 use the same claim-independent protected capture but never the same C1-0 source object or one-shot scope.

Each claim performs:

```text
durable capture
+ current exact claimed record
+ new scope
-> canonical C1-0 builder
-> fresh source
```

A stale or consumed source object remains invalid. C1-5 does not calculate retry delay, jitter, or attempt limits; those remain C1-2 authority.

## Terminal cleanup

The cleanup adapter is called only after a canonical B3 terminal transition has committed. It first releases any process-local hot-cache capture and then validates and removes the matching durable artifact.

Successful cleanup is immediate unlink plus directory fsync. If cleanup cannot complete, the helper returns `cleanup_required` and attempts to publish a bounded content-free cleanup marker. It never reverts a successful queue transition, never changes the queue record to retry, and never stores source content in the marker.

This slice does not add a background GC scanner. A future scheduler/service boundary may consume cleanup-required markers, but that authority is not introduced here.

## Missing and corrupt source semantics

C1-5 reports bounded reason identifiers only:

- missing artifact: `missing` / source unavailable;
- lock or filesystem contention: `retryable`;
- malformed, truncated, non-UTF-8, schema, identity, digest, symlink, non-regular, hardlink, or size failure: `corrupt`;
- same identity with different source: `collision`;
- cleanup failure after terminal commit: `cleanup_required`.

Raw exception text, artifact paths, identifiers, digests, namespace values, lineage values, messages, titles, summaries, and protected payloads are absent from public projections and workflow diagnostics.

## Configuration

Apply mode additionally requires:

```yaml
relaymem_slp_protected_source_root: /absolute/runtime-private/path
relaymem_slp_protected_source_max_artifact_bytes: 262144
```

The root must exist and be protected by deployment filesystem permissions. Dry-run mode remains usable without a durable source root.

## Verification

The dedicated smoke covers:

- create, read, restart rehydrate, equivalent duplicate, conflicting duplicate, and concurrent create-if-absent;
- canonical serialization, bounded size, schema drift, field drift, malformed/truncated/non-UTF-8 JSON, digest and identity tampering;
- symlink, directory, FIFO, traversal, hardlink-sensitive reads, and ignored temporary files;
- source-before-queue ordering and synchronous orphan cleanup;
- generation N retry release, fresh generation N+1 source/scope, stale source rejection, terminal convergence, and capture digest stability;
- terminal cleanup and cleanup-required behavior without queue rollback;
- real separate-process producer/restart-consumer execution through the production one-claimed worker;
- leakage canaries across queue JSON, projections, node results, repr, filenames, stdout, and stderr;
- C1-0, I1-B, B2, B3, C1-2, Thread G integrated fault, documentation, and onboarding regressions.

## Accurate completion boundary

> Phase 6-C1 is restart-complete for protected worker-source recovery. Next-turn Primary MEM recall remains unimplemented.
