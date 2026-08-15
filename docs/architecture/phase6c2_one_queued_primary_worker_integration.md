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
  - RT-1 Primary writer decision carriage changes
  - RT-1D-R5 or R6 retires the Primary worker path
relaylm_not_authoritative_for:
  - queue scanning, scheduling, polling, daemon, or worker-pool lifecycle
  - B3 queue state-machine or retry timing semantics
  - C1-5 protected artifact schema and integrity semantics
  - C1-2 M3a-M3h execution, classification, or transition semantics
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - next-turn recall, RelayCTX scope injection, or SOUL Lab observation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - ../contracts/slp/durable-queue.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - relaymem_slp_current_target.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../PROJECT_STATUS.md
---
# Phase 6-C2 One Queued Primary Worker Integration

Last reviewed: 2026-08-08 JST

## Status

Phase 6-C2 remains the implemented bounded adapter for one caller-selected canonical queued Primary job, but RT-1D-R4 now supplies an exact Primary writer decision before C2 may claim or execute that job:

```text
exact queued B3 record
  + exact RT-1 Primary writer decision
  -> rejected / malformed / foreign decision
       -> invalid_input
       -> no B3 claim mutation
       -> no protected-source consumption
       -> no C1-2 worker invocation
  -> permitted decision
       -> canonical B3 claim
       -> reread and validate current exact claim
       -> C1-5 protected-source lookup / rehydrate
       -> fresh C1-0 source and one-shot scope
       -> unchanged C1-2 one-claimed worker carrying the same decision
       -> canonical B3 retry release or terminal commit
       -> terminal-only protected-source cleanup
```

The production boundary remains `execute_one_queued_relaymem_slp_primary_job(...)` in `relaylm/relaymem_slp_one_queued_job_runner.py`.

C2 is therefore a retained Primary compatibility writer path, not independent current writer authority. RT-1 writer authorization remains owned by the cutover domain, and R5/R6 own final retirement/disposition of the replaced Primary worker surfaces.

## Ownership

- The caller owns selection of one exact queued record and carriage of the exact RT-1 Primary writer decision produced by the owning cutover boundary.
- The cutover domain exclusively owns whether the Primary writer class is `permitted` or `rejected`; C2 consumes that decision and never reconstructs it from queue, source, store, or configuration state.
- B3 exclusively owns claim CAS, revision/generation advancement, lease creation, fencing, retry release, stale recovery, and terminal commit.
- C1-5 exclusively owns durable protected-source lookup, integrity/identity validation, fresh C1-0 reconstruction, and terminal cleanup.
- C1-2 exclusively owns lease checkpoints, M3a-M3h execution order, outcome classification, retry timing, and final B3 transition.
- RelayMEM M3b-M3h continue to own memory-write idempotency and independently consume the carried writer decision through the worker/pipeline path.

C2 coordinates these existing production boundaries. It does not duplicate or redefine them, and a valid queued record or lease is never a substitute for RT-1 writer permission.

## Exact request

The runtime-private request carries:

- one exact `SubjectiveMemRetrievalPrimaryWriterDecision`,
- one exact canonical `queued` B3 record,
- one exact process-local source registry used only as an optional hot cache,
- exact character identity,
- absolute queue, protected-source, and RelayMEM store roots,
- exact claim owner,
- bounded lease duration,
- explicit `enabled`, `dry_run_only`, and `apply_enabled` gates,
- bounded protected-source artifact size.

Lookalike mappings, bool/int confusion, incomplete gate modes, relative roots, malformed queued records, schema drift, invalid tokens, or a non-permitted writer decision fail closed. For an enabled request, the writer decision is checked before C2 enters claim/source/worker execution.

C2 does not itself re-resolve durable cutover state. It consumes the exact immutable decision carried by its caller; the C1 worker and M3 pipeline then independently validate that same carried decision as defense in depth. B3 lease checkpoints remain lease fences only and must not be described as a substitute writer-state re-read.

## Writer gate

The current cutover owner defines the Primary writer class as `permitted` or `rejected`. Writes remain permitted only strictly before durable `primary_writer_fenced` in the owning cutover chain.

At the C2 entry point, any enabled request whose carried decision is not exactly permitted returns:

```text
status = invalid_input
reason = primary_writer_decision_rejected
claim_attempted = false
claim_performed = false
worker_invoked = false
```

The functional smoke additionally proves that the queue remains in `queued` state and the protected source remains present when the writer gate rejects the request. Historical queue success, an already-persisted protected source, prior Primary memory content, or a valid store root cannot re-authorize the writer.

The gate applies to enabled dry-run and apply invocations alike: dry-run may inspect the proposed C2 flow only when the carried writer decision is permitted. This keeps the compatibility path from treating diagnostic execution as an alternate authority surface.

## Dry-run and apply

Dry-run requires an exact permitted writer decision plus the canonical `(enabled=True, dry_run_only=True, apply_enabled=False)` mode. It performs the canonical B3 claim proposal and validates the matching durable protected-source artifact against that proposed exact claim. It does not:

- mutate the queue,
- construct or consume a C1-0 one-shot source,
- invoke C1-2,
- write RelayMEM,
- transition the queue,
- remove the protected artifact.

Apply requires an exact permitted writer decision plus the canonical `(enabled=True, dry_run_only=False, apply_enabled=True)` mode. Only then does it perform claim, current-claim revalidation, C1-5 preparation, and C1-2 execution in that order.

A `rejected`, foreign, malformed, or otherwise non-permitted decision is not converted into dry-run, retry, hold, or fallback behavior. It fails closed before claim/source/worker execution.

## Defensive downstream carriage

After C2 admits an exact permitted decision, that same immutable decision is carried into the C1 worker request and then into the M3 pipeline request.

The downstream boundaries independently fail closed:

```text
C2 entry
  -> primary_writer_decision_permits_write(...)
  -> C1 worker
       -> primary_writer_decision_permits_write(...)
       -> M3 pipeline
            -> primary_writer_decision_permits_write(...)
            -> only then protected-source consumption and M3 execution
```

These repeated checks preserve defense in depth if a future caller bypasses one wrapper. They do not give C2 authority to mint a replacement decision or to infer a new decision from B3 state.

## Claim-success source failures

After B3 claim succeeds under a permitted writer decision, source preparation distinguishes:

- `source_unavailable` for a missing artifact,
- `source_retryable` for store lock/contention or filesystem uncertainty,
- `source_blocked` for malformed JSON, schema drift, identity mismatch, integrity mismatch, unsafe file type, or reconstruction failure,
- `claim_lost_before_rehydrate` when the current claim fence no longer validates.

C2 does not invent a new queue terminal meaning or unbounded retry policy for these outcomes. The claimed record remains fenced and the durable artifact is retained when present; canonical lease expiry and B3 stale recovery remain the recovery authority. Queue metadata, trace, frontend history, visible output, or public projections are never used to reconstruct protected content.

These source/lease outcomes occur only after writer authorization has admitted the C2 path; none of them can convert a rejected writer decision into permission.

## Retry, stale claims, and cleanup

- C1-2 retry release retains the durable source.
- A later claim receives a new generation and fresh source/scope, but still requires the caller-carried exact writer decision for that invocation.
- A losing claim race never reaches source preparation or worker invocation.
- A stale generation cannot consume a current source or transition the queue.
- Terminal cleanup starts only after C1-2 has durably committed a terminal B3 state.
- Cleanup failure is reported as `cleanup_required` and never rolls back the terminal queue state.

Queue retry/stale-recovery mechanics do not own RT-1 writer authorization. A retryable queued record is work availability, not permission to execute the Primary writer.

## Content-free projection

The public projection exposes only bounded status, gate values, claim/source/worker booleans and statuses, retryable/terminal flags, cleanup-required state, and reason IDs. It omits all content, identifiers, namespace/lineage values, idempotency keys, claim fences, timestamps, paths, digests, exception text, private writer-decision identity, and private nested result representations.

## Verification

Dedicated Phase 6-C2 coverage includes:

- exact writer-decision rejection before claim/source/worker execution,
- normal queued-to-terminal success and terminal cleanup,
- dry-run non-mutation,
- M3g lock-contention retry release, retained source, fresh later claim, and success,
- separate-process producer/restart-consumer rehydration,
- competing claim attempts with only one worker invocation,
- missing, malformed, wrong-schema, identity-mismatched, digest-mismatched, and symlink source artifacts,
- claim loss before rehydration,
- content-free result, node projection, repr, stdout, and stderr,
- B2, B3, C1-2, C1-4, C1-5, compile, and documentation regressions.

The workflow/test registry remains the command authority; this list records the C2 regression boundary rather than defining a second CI registry.

## Accurate completion boundary

> I1-B production, B3 lifecycle, C1-0 through C1-5, and the C2 one-job claim/rehydrate/execute adapter are complete as implemented capabilities. Under current RT-1 semantics the Primary worker path executes only with an exact permitted writer decision. Queue scanning/scheduling, daemon/service lifecycle, and other historically separate slices remain outside C2 ownership; their repository-wide implementation status is owned by Project Status and their own current authorities.

This completion statement is capability/history evidence. It does not preserve independent Primary mutation authority after the owning cutover boundary rejects the writer, and it does not claim R5 retirement complete.

## Phase I-1 downstream completion

Phase I-1 is complete. The C2 `store_root` supplied by a production caller is resolved with the same opaque character-partition function used by the retained Primary compatibility branch of ordinary Turn 2 retrieval. C2 itself remains structurally the same one-job adapter after the writer gate: exact queued B3 record, canonical B3 claim, C1-5 protected-source lookup / rehydrate, and C1-2 one-claimed worker.

Phase I-1 completion does not make C2 reader authority, and reader retirement remains separately governed by RT-1D-R5/R6.

## RT-1D-R5 / R6 boundary

Current Project Status records R4 activation/P8 complete and R5 immediate retirement unstarted. C2 therefore remains a live retained Primary compatibility surface, but its execution is subordinate to the exact writer decision described above.

R5/R6 own the final retirement or explicitly retained read-only disposition of C2/Primary worker surfaces after exact dependency characterization. This handoff does not authorize deleting runtime code, queue evidence, protected-source history, or tests ahead of that owning transaction.

Retirement must not be simulated by weakening C2 validation, bypassing the writer decision, treating `rejected` as dry-run or retry, or moving Primary mutation semantics into another owner.
