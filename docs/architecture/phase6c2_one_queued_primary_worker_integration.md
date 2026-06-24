---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c2_one_queued_primary_worker_integration
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - one queued-job adapter request/result schema changes
  - B3 claim, C1-5 preparation, or C1-2 invocation ownership changes
  - protected-source failure or terminal cleanup handling changes
relaylm_not_authoritative_for:
  - queue scanning, scheduling, polling, daemon, or worker-pool lifecycle
  - B3 queue state-machine or retry timing semantics
  - C1-5 protected artifact schema and integrity semantics
  - C1-2 M3a-M3h execution, classification, or transition semantics
  - next-turn recall, RelayCTX scope injection, or SOUL Lab observation
relaylm_related_authority:
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - relaymem_slp_current_target.md
---
# Phase 6-C2 One Queued Primary Worker Integration

## Status

Phase 6-C2 completes the bounded E-to-F integration for one caller-selected, canonical queued job:

```text
exact queued B3 record
  -> canonical B3 claim
  -> reread and validate current exact claim
  -> C1-5 protected-source lookup / rehydrate
  -> fresh C1-0 source and one-shot scope
  -> unchanged C1-2 one-claimed worker
  -> canonical B3 retry release or terminal commit
  -> terminal-only protected-source cleanup
```

The production boundary is `execute_one_queued_relaymem_slp_primary_job(...)` in `relaylm/relaymem_slp_one_queued_job_runner.py`.

## Ownership

- The caller owns selection of one exact queued record.
- B3 exclusively owns claim CAS, revision/generation advancement, lease creation, fencing, retry release, stale recovery, and terminal commit.
- C1-5 exclusively owns durable protected-source lookup, integrity/identity validation, fresh C1-0 reconstruction, and terminal cleanup.
- C1-2 exclusively owns lease checkpoints, M3a-M3h execution order, outcome classification, retry timing, and final B3 transition.
- RelayMEM M3b-M3h continue to own memory-write idempotency.

C2 coordinates these existing production boundaries. It does not duplicate or redefine them.

## Exact request

The runtime-private request carries:

- one exact canonical `queued` B3 record,
- one exact process-local source registry used only as an optional hot cache,
- exact character identity,
- absolute queue, protected-source, and RelayMEM store roots,
- exact claim owner,
- bounded lease duration,
- explicit `enabled`, `dry_run_only`, and `apply_enabled` gates,
- bounded protected-source artifact size.

Lookalike mappings, bool/int confusion, incomplete gate modes, relative roots, malformed queued records, schema drift, or invalid tokens fail closed before claim mutation.

## Dry-run and apply

Dry-run performs the canonical B3 claim proposal and validates the matching durable protected-source artifact against that proposed exact claim. It does not:

- mutate the queue,
- construct or consume a C1-0 one-shot source,
- invoke C1-2,
- write RelayMEM,
- transition the queue,
- remove the protected artifact.

Apply requires the exact `(enabled=True, dry_run_only=False, apply_enabled=True)` mode. It performs claim, current-claim revalidation, C1-5 preparation, and C1-2 execution in that order.

## Claim-success source failures

After B3 claim succeeds, source preparation distinguishes:

- `source_unavailable` for a missing artifact,
- `source_retryable` for store lock/contention or filesystem uncertainty,
- `source_blocked` for malformed JSON, schema drift, identity mismatch, integrity mismatch, unsafe file type, or reconstruction failure,
- `claim_lost_before_rehydrate` when the current claim fence no longer validates.

C2 does not invent a new queue terminal meaning or unbounded retry policy for these outcomes. The claimed record remains fenced and the durable artifact is retained when present; canonical lease expiry and B3 stale recovery remain the recovery authority. Queue metadata, trace, frontend history, visible output, or public projections are never used to reconstruct protected content.

## Retry, stale claims, and cleanup

- C1-2 retry release retains the durable source.
- A later claim receives a new generation and fresh source/scope.
- A losing claim race never reaches source preparation or worker invocation.
- A stale generation cannot consume a current source or transition the queue.
- Terminal cleanup starts only after C1-2 has durably committed a terminal B3 state.
- Cleanup failure is reported as `cleanup_required` and never rolls back the terminal queue state.

## Content-free projection

The public projection exposes only bounded status, gate values, claim/source/worker booleans and statuses, retryable/terminal flags, cleanup-required state, and reason IDs. It omits all content, identifiers, namespace/lineage values, idempotency keys, claim fences, timestamps, paths, digests, exception text, and private nested result representations.

## Verification

Dedicated Phase 6-C2 coverage includes:

- normal queued-to-terminal success and terminal cleanup,
- dry-run non-mutation,
- M3g lock-contention retry release, retained source, fresh later claim, and success,
- separate-process producer/restart-consumer rehydration,
- competing claim attempts with only one worker invocation,
- missing, malformed, wrong-schema, identity-mismatched, digest-mismatched, and symlink source artifacts,
- claim loss before rehydration,
- content-free result, node projection, repr, stdout, and stderr,
- B2, B3, C1-2, C1-4, C1-5, compile, and documentation regressions.

## Accurate completion boundary

> I1-B production, B3 lifecycle, C1-0 through C1-5, and the C2 one-job claim/rehydrate/execute adapter are complete. Queue scanning/scheduling, daemon/service lifecycle, pre-enqueue background-finalizer crash recovery, next-turn recall and scope isolation, SOUL Lab real observation, memory correction, and Secondary MEM remain outside this slice.

## Phase I-1 downstream completion

Phase I-1 is complete. The C2 `store_root` supplied by a production caller is
resolved with the same opaque character-partition function used by ordinary
Turn 2 retrieval. C2 itself remains unchanged: exact queued B3 record,
canonical B3 claim, C1-5 protected-source lookup / rehydrate, and unchanged
C1-2 one-claimed worker. Queue scanning/scheduling and pre-enqueue
background-finalizer crash recovery remain out of scope.
