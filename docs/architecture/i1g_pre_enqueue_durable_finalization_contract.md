---
relaylm_doc_type: contract
relaylm_authority: i1g_pre_enqueue_durable_finalization_contract_publication_replay_completion_and_retention
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - I1-GB durable-finalization publication changes
  - I1-GC one-record replay or completion semantics change
  - I1-GD retention or cleanup semantics change
  - I1-GE production crash-smoke evidence lands
  - O1B sealed-record discovery lands
  - I1-B finalized-turn identity or response-finalization order changes
relaylm_not_authoritative_for:
  - I1-GD exact production behavior beyond the dedicated handoff
  - I1-GE exact crash-validation harness beyond the dedicated handoff
  - O1 scheduler discovery polling fairness or service lifecycle
  - C1-5 protected-source schema or persistence semantics
  - B2 or B3 queue schema and lifecycle semantics
  - C1-0 C1-2 C2 or M3a-M3h worker and memory semantics
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - i1gd_durable_finalization_retention_cleanup.md
  - i1ge_durable_finalization_crash_validation.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c2_one_queued_primary_worker_integration.md
  - o1a_two_lane_scheduler_contract.md
  - o1d1_production_scheduler_round.md
  - wave3_cross_slice_convergence_audit.md
  - pipeline_implementation_plan.md
  - post_i3_evaluation_work_roadmap.md
---
# I1-G Pre-enqueue Durable-finalization Contract and Replay Boundary

## Status and authority

I1-GA through I1-GE are complete:

- I1-GA is complete as the contract, design decision, pure fault model, and validation boundary.
- I1-GB is complete for bounded durable base/segment/seal publication and response-release admission.
- I1-GC is complete for caller-selected one-record restart replay, exact C1-5/B2 convergence, duplicate suppression, cross-process fencing, canonical downstream verification, and immutable completion markers.
- I1-GD is complete for bounded retention, orphan reconciliation, content-free isolation, and crash-convergent cleanup.
- I1-GE is complete as validation-only real process-exit/fresh-restart proof across the existing I1-GB through I1-GD production authorities.

I1-G overall is complete only for sealed durable-finalization evidence, exact C1-5 source, exact B2 queue correlation, durable completion, retention/isolation lifecycle, and crash-at-every-boundary validation. It does not imply B3 terminal success, C2 execution, worker execution, Primary MEM formation, semantic quality, retrieval use, automatic scheduling, polling, supervision, or always-on operation.

O1A defines only the scheduler-side two-lane round contract. O1B is complete for one bounded eligible sealed-record discovery, canonical selected-record reread, and at most one I1-GC call. O1C is complete for one independent bounded B2/B3 queue discovery, canonical reread, server-owned scope resolution, and at most one existing C2 call. O1D1 is complete for accepted scheduler gates and one caller-invoked replay-before-queue round. None of O1A through O1D1 owns I1-G replay, completion, C1-5, B2/B3 lifecycle, retention, cleanup, or worker execution.

## Problem and resolved recovery window

Explicit I1-GB apply mode uses:

```text
backend response
  -> final safe visible response / parsed SSE unit
  -> exact I1-B source and A1 -> A2 -> B1 preparation
  -> private base / segment / seal publication and canonical reread
  -> HTTP body, protected SSE unit, or terminal completion release
  -> normal finalizer
       -> shared I1-GC convergence authority
       -> canonical C1-5 durable protected source
       -> canonical B2 content-free queue record
       -> immutable completion marker
```

Window A is resolved by completed publication, replay, retention, and crash-validation boundaries:

```text
Window A publication side — implemented by I1-GB
  restart evidence is durable before protected visible release

Window A recovery side — implemented by I1-GC
  process exits after seal but before C1-5/B2/completion
    -> one caller-selected sealed record is replayable
    -> exact C1-5 then exact B2 convergence
    -> durable completion marker

Window A retention/isolation side — implemented by I1-GD
  complete or invalid records converge through retain | isolate | cleanup | block

Window A validation side — implemented by I1-GE
  real process exits and fresh-process restarts prove the existing authorities
```

Window B remains resolved by C1-5 + B3 + C2 + C1-2 restart convergence after durable source and queue publication.

## Chosen design

The canonical record is one turn-scoped sealed durable-finalization publication record:

```text
schema_version = relaymem.slp_durable_finalization.v0
runtime_private = true
content_included = true
```

It is not a generic journal, worker outbox, second queue, or memory lifecycle. One logical record consists of:

```text
base record             exact run/turn/character correlation
zero or more segments   stream only; bounded, append-only, hash-chained
seal marker             exact finalized turn + exact B1 job/dispatch identity
completion marker       exact C1-5 + B2 convergence verified
isolation marker        I1-GD content-free forward-only cleanup evidence
per-record replay fence shared by I1-GC and I1-GD
```

The isolation schema is `relaymem.slp_durable_finalization_isolation.v0`; its exact behavior belongs to [I1-GD Durable-finalization Retention and Cleanup](i1gd_durable_finalization_retention_cleanup.md).

## Authority diagram

```text
request runtime
  -> I1-B finalized-turn meaning and exact B1 identity
  -> I1-G durable evidence / replay / completion / retention / crash proof
  -> C1-5 protected-source persistence
  -> B2 content-free queue publication
  -> B3 queue lifecycle
  -> C2 one queued-record coordination
  -> C1-0 / C1-2 worker
  -> M3a-M3h Primary MEM persistence
```

I1-G completion means only:

- the sealed record is valid;
- exact finalized-turn reconstruction reproduces the sealed B1 identity;
- exact C1-5 protected source is canonically valid;
- exact B2 queue record is canonically valid and correlated;
- source-before-queue is preserved;
- the immutable completion marker is durably published and reread;
- retention/isolation lifecycle is bounded and marker-last;
- real process-exit/fresh-restart proof covers the production boundaries.

It does not mean B3 terminal success, worker execution, Primary MEM formation, semantic quality, or retrieval use.

## Commit and release ordering

For non-stream, the complete record is sealed before body release. For stream, each bounded segment is durable before the corresponding visible bytes are yielded, and the final seal is durable before terminal completion is released.

```text
private base commit/reread
  -> each stream segment commit/reread before yield
  -> exact finalized source
  -> existing A1/A2/B1 builders
  -> seal commit/reread with exact B1 identity
  -> non-stream body or stream terminal release
  -> normal finalizer or caller-selected restart replay
       -> canonical C1-5 persist/converge
       -> canonical B2 enqueue/converge
       -> exact downstream correlation reread
       -> completion marker commit/reread
  -> caller-selected I1-GD bounded retention/cleanup pass
```

The source-before-queue invariant is absolute:

```text
valid C1-5 protected source durable
  before
claimable canonical B2 queue record
```

## One-record I1-GC replay algorithm

1. Accept one caller-selected deterministic locator digest; do not scan.
2. Open the configured root securely and acquire a nonblocking cross-process per-record exclusive fence.
3. Canonically reread base, ordered segments, seal, and completion marker.
4. Return `already_complete` for an exact valid completion without mutation.
5. Reject incomplete, isolated, unsupported, corrupt, unsafe, collision, and impossible states without replay.
6. Reconstruct the exact finalized-turn production type from sealed evidence.
7. Invoke existing A1/A2/B1 preparation without inventing replacement time, turn, job, dispatch, namespace, lineage, or content.
8. Require exact equality between reconstructed B1 identity and sealed durable job/dispatch identity.
9. Inspect C1-5: publish if absent; continue only for exact equivalent; fail closed for collision/corruption/unsafe/ambiguous state.
10. Inspect B2 only after exact source proof: publish if absent; continue only for exact equivalent; fail closed otherwise.
11. Treat queue-present/source-absent as an invariant violation; never fabricate source or delete queue.
12. Resolve ambiguous mutation outcomes only by canonical reread.
13. Verify exact job, dispatch, character, and source-before-queue correlation.
14. Leave an exact terminal B3 record unchanged; it may still satisfy I1-G completion proof.
15. Publish the immutable completion marker with no-clobber semantics, directory durability, and canonical reread.
16. Release the fence and return a bounded content-free result.

No discovery, directory scanner, polling, sleep, retry loop, scheduler, B3 transition, C2 execution, worker execution, M3 write, or cleanup belongs in I1-GC.

## I1-GD maintenance algorithm

1. Validate the separate retention gate and absolute private root.
2. Build a complete bounded non-recursive inventory before inferring absence.
3. Group known canonical components by locator and process locators deterministically.
4. Keep unsafe or unclassifiable objects completely non-destructive.
5. Acquire the exact I1-GC per-record fence; while held, acquire the existing I1-GB root mutation lock.
6. Canonically reread and classify fresh incomplete, expired orphan, sealed pending, valid complete, isolated, corrupt, unsupported, ambiguous, or blocked state.
7. Retain sealed pending records without an age-based cleanup path.
8. Before any component reclamation, publish `relaymem.slp_durable_finalization_isolation.v0` no-clobber, fsync the directory, and reread it exactly.
9. Reclaim only stable known canonical components, with secure inode/type/link-count/size/mtime checks.
10. Fsync the directory and retain the isolation marker for its configured horizon.
11. Remove the isolation marker last only after no logical components remain.
12. Never remove the per-record lock file and never mutate C1-5, B2, B3, C2, worker, or M3 state.
13. Return one bounded content-free result without polling or sleeping.

## I1-GE validation boundary

I1-GE proves the existing production authorities with real child-process `os._exit` seams and fresh child interpreters for restart convergence. It covers non-stream publication/visible release, stream publication/protected yield/terminal release, I1-GC reconstruction/C1-5/B2/completion, normal-finalizer/restart replay races, same-locator replay concurrency, O1B discovery integration, and I1-GD retention/isolation/cleanup.

I1-GE changes no durable schema, replay algorithm, accepted configuration, scheduler, queue lifecycle, worker behavior, memory lifecycle, daemon, service supervision, or SOUL Lab UI.

## Idempotency, duplicate, and race convergence

- Exact repeated replay produces no new source, queue record, or completion marker.
- Exact repeated isolation publication converges as a duplicate; different marker content at the same locator is a collision.
- Exact C1-5 and B2 duplicates count only after canonical reread.
- Same locator with different content or identity is a collision and fails closed.
- I1-GC and I1-GD use the same per-record fence. I1-GD also holds the existing I1-GB root mutation lock during reread and cleanup, excluding publication overlap.
- Two maintenance processes race through a nonblocking `flock`; one winner progresses and the other returns bounded contention.
- C1-5 and B2 retain their own no-clobber uniqueness authority.
- I1-G completion suppresses only finalization replay; it does not replace B3, C1-2, M3, or mutation idempotency.
- `isolation marker + remaining components` is a normal forward-recovery state after interruption.

## Security and content-free projection

Roots are absolute, pre-existing, runtime-private, permission-protected directories. Reads and writes reject symlinks, hardlinks, unsafe file types, path escape, duplicate JSON keys, malformed/noncanonical UTF-8/JSON, unknown fields, non-finite values, size overflow, and changed inode/type during reread.

Public results, logs, `repr`, PipelineNodeResult, browser surfaces, and scheduler projections must omit:

- user/assistant text and governed memory content;
- namespace values;
- run/session/turn/job/dispatch/lineage identities;
- locator/digest/path values;
- lease tokens and exact timestamps;
- raw exceptions and nested protected results.

## Current configuration

I1-GB and I1-GC use the existing default-off durable-finalization settings:

```yaml
relaymem_slp_durable_finalization_enabled: false
relaymem_slp_durable_finalization_dry_run_only: true
relaymem_slp_durable_finalization_apply_enabled: false
relaymem_slp_durable_finalization_root:
relaymem_slp_durable_finalization_max_record_bytes: 524288
relaymem_slp_durable_finalization_max_segment_bytes: 65536
relaymem_slp_durable_finalization_max_segment_count: 256
relaymem_slp_durable_finalization_max_record_count: 1024
relaymem_slp_durable_finalization_publication_timeout_ms: 5000
```

I1-GD has a separate default-off, dry-run-first gate:

```yaml
relaymem_slp_durable_finalization_retention_enabled: false
relaymem_slp_durable_finalization_retention_dry_run_only: true
relaymem_slp_durable_finalization_retention_apply_enabled: false
relaymem_slp_durable_finalization_completed_retention_seconds: 604800
relaymem_slp_durable_finalization_orphan_grace_seconds: 86400
relaymem_slp_durable_finalization_isolated_retention_seconds: 2592000
relaymem_slp_durable_finalization_cleanup_max_records_per_pass: 64
relaymem_slp_durable_finalization_cleanup_timeout_ms: 5000
```

Apply requires the exact enabled/dry-run/apply gate combination, valid absolute private roots, and positive bounds. No setting enables a scanner loop, polling loop, retry scheduler, daemon, or service.

## O1 caller boundary

O1B performs one bounded non-recursive discovery, secure eligibility classification, deterministic one-candidate selection, canonical reread, and at most one I1-GC call. It must not reconstruct protected content, call C1-5/B2 directly, decide completion independently, pass replay output directly to C2, extract job/dispatch identity for the queue lane, scan repeatedly, sleep, retry, or execute a worker.

O1D1 may call O1B at most once and then O1C at most once in one round. After replay, the queue lane independently discovers the queue root through O1C. Same-round execution of a newly converged B2 record is possible but not guaranteed or specially prioritized.

## Validation boundary

I1-GC validation covers sealed-only, source-only, source+queue, exact duplicate, repeated replay, two-process contention, normal-finalizer/restart race, C1-5-to-B2 interruption, B2-to-completion interruption, ambiguous mutation outcomes, terminal B3 preservation, corrupt/noncanonical/unsupported evidence, unsafe links/types, dry-run/nonexecution, and content-leakage canaries.

I1-GD validation covers default-off and dry-run gates, bounded inventory, fresh/expired incomplete records, sealed-pending retention, exact completion cleanup eligibility, corrupt/unsupported isolation, marker duplicate/collision behavior, interrupted cleanup convergence, marker-last deletion, shared-fence contention, root-lock publication exclusion, unsafe-file non-mutation, future-clock retention, downstream non-mutation, replay exclusion after isolation, and leakage canaries.

I1-GE validation covers real process-exit/fresh-restart proof at the existing publication, replay, completion, concurrency, retention, and leakage boundaries.
