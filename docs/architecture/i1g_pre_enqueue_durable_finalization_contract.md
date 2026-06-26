---
relaylm_doc_type: contract
relaylm_authority: i1g_pre_enqueue_durable_finalization_contract_publication_replay_and_completion
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
  - I1-GD retention and cleanup production behavior
  - I1-GE full crash-at-every-boundary proof
  - O1 scheduler discovery polling fairness or service lifecycle
  - C1-5 protected-source schema or persistence semantics
  - B2 or B3 queue schema and lifecycle semantics
  - C1-0 C1-2 C2 or M3a-M3h worker and memory semantics
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c2_one_queued_primary_worker_integration.md
  - o1a_two_lane_scheduler_contract.md
  - pipeline_implementation_plan.md
  - post_i3_evaluation_work_roadmap.md
---
# I1-G Pre-enqueue Durable-finalization Contract and Replay Boundary

## Status and authority

I1-GA is complete as the contract, design decision, pure fault model, and validation boundary. I1-GB is complete for bounded durable base/segment/seal publication and response-release admission. I1-GC is complete for caller-selected one-record restart replay, exact C1-5/B2 convergence, duplicate suppression, cross-process fencing, canonical downstream verification, and immutable completion markers.

I1-GD retention/cleanup and I1-GE full production crash validation remain unimplemented. I1-G overall remains in progress until those boundaries land.

O1A defines only the scheduler-side two-lane round contract. Future O1B discovers at most one eligible sealed record, canonically rereads eligibility, and calls I1-GC once. O1B does not own replay, completion, C1-5, or B2.

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

Window A is now split into completed publication and replay boundaries:

```text
Window A publication side — implemented by I1-GB
  restart evidence is durable before protected visible release

Window A recovery side — implemented by I1-GC
  process exits after seal but before C1-5/B2/completion
    -> one caller-selected sealed record is replayable
    -> exact C1-5 then exact B2 convergence
    -> durable completion marker
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
isolation marker        future I1-GD bounded control evidence
```

## Authority diagram

```text
request runtime
  -> I1-B finalized-turn meaning and exact B1 identity
  -> I1-G durable evidence / replay / completion
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
- the immutable completion marker is durably published and reread.

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
  -> future I1-GD retention/cleanup
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
5. Reject incomplete, unsupported, corrupt, unsafe, collision, and impossible states without replay.
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

## Idempotency, duplicate, and race convergence

- Exact repeated replay produces no new source, queue record, or completion marker.
- Exact C1-5 and B2 duplicates count only after canonical reread.
- Same locator with different content or identity is a collision and fails closed.
- The normal I1-GB finalizer and restart replay use the same per-record fence and completion authority.
- Two processes race through a nonblocking `flock`; one winner progresses and the other returns bounded contention.
- C1-5 and B2 retain their own no-clobber uniqueness authority.
- I1-G completion suppresses only finalization replay; it does not replace B3, C1-2, M3, or mutation idempotency.

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

Apply requires the exact enabled/dry-run/apply gate combination, valid absolute private roots, and positive bounds. No setting enables a scanner, polling loop, retry scheduler, daemon, or service. O1A scheduler names remain target-only and are not accepted configuration.

## O1B caller boundary

Future O1B may perform one bounded non-recursive discovery, secure eligibility classification, deterministic one-candidate selection, canonical reread, and one I1-GC call. It must not:

```text
reconstruct protected content
call C1-5 or B2 directly
decide completion independently
pass replay output directly to C2
extract job/dispatch identity for the queue lane
scan repeatedly, sleep, retry, or execute a worker
```

After replay, the queue lane independently discovers the queue root. Same-round execution of a newly converged B2 record is possible but not guaranteed or specially prioritized.

## Remaining slices

### I1-GA — complete

Contract, authority, record, fault, projection, security, and validation model.

### I1-GB — complete

Durable base/segment/seal publication, canonical reread, exact preparation, and pre-release/pre-yield admission.

### I1-GC — complete

One caller-selected sealed-record replay through existing A1/A2/B1, C1-5, and B2 authorities; cross-process fencing; exact duplicate convergence; downstream reread; immutable completion marker; normal-finalizer integration.

### I1-GD — unimplemented

Bounded retention, orphan reconciliation, isolation lifecycle, and cleanup for incomplete, sealed, complete, orphan, corrupt, unsupported, and isolated records.

### I1-GE — unimplemented

Full production crash-at-every-boundary integration smoke across non-stream, stream, publication, visible release, C1-5, B2 ambiguity, completion, concurrency, restart, retention, and leakage.

### O1B through O1F — unimplemented

Production discovery, queue-lane delegation, ordering/fairness/retry policy, stale recovery/shutdown, and operational validation.

## Validation boundary

I1-GC validation covers sealed-only, source-only, source+queue, exact duplicate, repeated replay, two-process contention, normal-finalizer/restart race, C1-5-to-B2 interruption, B2-to-completion interruption, ambiguous mutation outcomes, terminal B3 preservation, corrupt/noncanonical/unsupported evidence, unsafe links/types, dry-run/nonexecution, and content-leakage canaries.

Current status documents must describe I1-GC as complete and must not retain a contradictory pending statement followed by a later superseding section.
