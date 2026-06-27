---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_i4c2_primary_forget_recovery_finalization
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: relaymem_soul_lab_integration
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - phase_i4d_primary_retrieval_exclusion.md
  - wave2_cross_slice_convergence_audit.md
relaylm_not_authoritative_for:
  - I-4D ordinary retrieval exclusion
  - I-4E API or UI
  - I-4F product validation
---
# Phase I-4C2 Primary Forget Recovery and Finalization

Status: complete for the bounded I-4C2 one-operation recovery/finalization boundary.

## Authority and ownership

I-4C2 resumes one exact durable Forget operation and converges it forward through existing Primary page and control authorities:

```text
relaylm.mem.forget_prepared.v0
  -> exact deterministic hidden successor through I-4C1 / M3e
  -> canonical hidden-page reread
  -> operation-scoped M3f-compatible index/log plan
  -> existing M3g ordered atomic apply (index before log)
  -> canonical page/control correlation reread
  -> immutable relaylm.mem.forget_tombstone.v0
  -> exact replay from tombstone
  -> hidden / none / retrieval_eligible=false
```

The phase ownership split is:

```text
I-4C1:
  exact prepared artifact
  deterministic hidden lifecycle page
  M3e page durability and canonical reread

I-4C2:
  one exact prepared-operation resume
  forward-only hidden continuation
  exact one-operation index/log convergence
  page/control/prepared correlation
  tombstone finalization and exact replay

I-4D:
  ordinary M2 lifecycle eligibility enforcement
  prior physical revision exclusion
  RelayCTX injection exclusion
  prepared/recovery/corrupt fail-closed candidate filtering
  historical lifecycle projection
```

I-4C2 therefore does not claim product-complete Forget behavior or ordinary retrieval exclusion. `retrieval_exclusion_claimed` remains `false` in the tombstone because I-4D owns that runtime path.

## Production boundaries

The public production entry points are:

```python
apply_primary_memory_forget(...)
recover_primary_memory_forget(...)
```

`apply_primary_memory_forget` accepts one exact I-4B binding and supports exact external replay. `recover_primary_memory_forget` accepts one caller-selected `namespace + memory_id + operation_id`; it never scans all memories, issues a token, or starts a new operation without durable evidence.

Both boundaries use the sole shared Correct/Forget lock:

```text
memory/mem/corrections/v0/<logical-memory-id>/.lock
```

No second Forget lock exists.

## Durable artifact model

I-4C2 uses Option A: the tombstone is the sole durable applied-replay authority. There is no separate `forget_applied` receipt carrying the same semantic state.

### Prepared continuation authority

The existing immutable `relaylm.mem.forget_prepared.v0` remains unchanged. It binds character, namespace, logical memory, prior and result revisions, prior and successor physical identities, operation key, binding digest, reason digest, token digest, source kind, memory kind, lineage, deterministic page path and digest, and durable request/prepare timestamps.

After prepare exists, internal recovery can continue after token expiry. External replay must still provide the exact original operation, reason, and token digest.

### Tombstone authority

Schema: `relaylm.mem.forget_tombstone.v0`.

Finalized meaning is fixed:

```text
result_lifecycle_state = hidden
page_converged = true
index_converged = true
log_converged = true
retrieval_exclusion_claimed = false
status = reconciled
recovery_required = false
```

The reason remains runtime-private audit content and is excluded from result, `repr`, and log projections.

`tombstone_id` is deterministic over the logical memory, operation key, binding, prior/result revisions, prior/result physical identities, prepared digest, and result page digest. Time and randomness are not identity authority. The `applied_at` value is derived from already durable prepare evidence so an ambiguous final publication can be reconstructed byte-for-byte.

## Secure publication

Prepared and tombstone artifacts share the existing memory-scoped mutation root:

```text
memory/mem/corrections/v0/<memory_id>/
  <operation_key>.prepared.json
  <operation_key>.tombstone.json
```

Tombstone publication requires canonical UTF-8 JSON, exact fields, duplicate-key and non-finite rejection, bounded bytes, regular-file and `nlink == 1` checks, no symlink/path escape, create-if-absent no-clobber publication, file fsync, directory fsync, canonical reread, and collision detection. An existing exact canonical tombstone is idempotent; different bytes at the same identity are an operation conflict.

## Exact replay ordering

External apply uses this order:

```text
bounded input shape
  -> shared per-memory lock
  -> exact tombstone lookup
  -> exact prepared lookup
  -> tombstone exact binding replay, if present
  -> prepared exact binding continuation, if present
  -> otherwise release and enter completed I-4C1 live-token commit boundary
  -> reacquire shared lock
  -> exact prepared reread
  -> forward-only convergence
```

The initial lock release before invoking I-4C1 does not create a second commit authority. I-4C1 obtains the same lock, revalidates the live token and current revision, and publishes the no-clobber prepared artifact. A competing winner therefore produces an exact replay, conflict, stale target, or already-hidden result; it cannot create two successor revisions.

A finalized exact retry is checked before token expiry. The same operation ID with a different reason or token digest is not idempotent replay.

## State matrix

### No durable operation

Internal recovery returns bounded `not_recoverable` and performs no write. External apply delegates the new prepare/hidden commit to I-4C1.

### Prepared only

```text
active N + exact prepared + no hidden page
```

Recovery rereads the exact prepared artifact, reconstructs the deterministic I-4C1 candidate, publishes the exact hidden page through M3e, rereads it, and continues. It never creates a new operation ID, timestamp, candidate, physical ID, path, or digest.

### Hidden page, prior controls

```text
hidden N+1 durable
index/log still point to prior active evidence
```

The hidden page is never rolled back. I-4C2 reconstructs exact receipt-equivalent M3e evidence from the prepared artifact and canonical page, then builds the operation-scoped deterministic control plan.

### Index applied, log pending

The existing ordered atomic control apply authority sees the proposed index as an idempotent no-op and applies only the missing log append. No second page or second index entry is created.

### Controls converged, tombstone absent

I-4C2 rebuilds the plan from fresh control rereads and requires `already_reconciled` for both index and log before publishing the tombstone.

### Tombstone present

The prepared/tombstone/page/control chain is validated and the original bounded result is returned with `idempotent_replay=true`. No mutation occurs.

### New operation against finalized hidden state

A different valid pre-issued operation returns bounded `already_hidden` and does not create a new revision.

### Corrupt or ambiguous chain

Conflicting prepared/page/control/tombstone evidence, wrong revision or physical lineage, unsafe files, multiple tombstones, or impossible Correct/Forget chains fail closed as `target_corrupt`, `operation_conflict`, or `reconciliation_required`. The resolver returns non-retrievable corrupt state; no rollback or guessed repair occurs.

## PR #407 concurrent-loser normalization

The Wave 2 follow-up correction merged in PR #407 normalizes public concurrent-loser outcomes. This table is part of the I-4C2 authority and is consumed by later phases:

| Fresh current-state observation during apply/retry | Required public outcome |
|---|---|
| finalized `hidden / none` from another winner | `already_hidden` |
| hidden prepared or hidden recovery-required | `target_not_active` |
| hidden corrupt | `target_corrupt` |
| active but stale target revision or physical identity | `stale_revision` |

These outcomes are not repair actions. They are bounded public classifications after canonical reread under the shared lock. They do not create a new revision, do not roll back a hidden successor, and do not rewrite tombstone or prepared evidence.

## M3f/M3g reuse

The ordinary public M3f/M3g verifier intentionally validates active evidence pages. I-4C2 adds a narrow hidden-lifecycle adapter that validates the exact hidden page against the I-4C1 prepared artifact, reconstructs the exact M3e receipt shape from canonical durable evidence, calls the existing deterministic `build_index_plan` and `build_log_plan`, calls the existing ordered atomic `apply_or_inspect_reconciliation` I/O, rebuilds the plan after apply, and requires both controls to be idempotent no-ops.

The adapter does not directly edit `index.md` or `log.md`, does not introduce a second control writer, and preserves index-before-log ordering, control locking, atomic replacement, fsync, and conflict detection.

## Current-state resolver

The read-only resolver understands valid tombstone evidence before the I-4C1 prepared/hidden projection:

```text
prepared only:
  active / prepared / false

hidden page or incomplete controls:
  hidden / recovery_required / false

exact tombstone and exact controls:
  hidden / none / false

corrupt or ambiguous:
  hidden-safe / corrupt / false
```

The resolver never writes or invokes recovery. The shared current-state index and mutation coordinator recognize Forget prepared and tombstone artifacts, keep correction history limited to correction receipts, and preserve a single revision chain across Correct and Forget operations.

## Concurrency invariants

The shared lock and operation scanner establish:

```text
prepared Forget blocks new Correct
prepared Correct blocks new Forget
same exact Forget resumes or replays
different Forget bindings have one winner
hidden finalized state rejects new Correct/Forget commit
recovery and explicit retry converge to one tombstone
```

The PR #407 normalization table defines the public loser outcomes for already-hidden, hidden-in-progress, hidden-corrupt, and stale-active rereads. No snapshot read outside the shared lock is commit authority.

## Fault and response-loss convergence

Production seams cover:

```text
after_lock_before_operation_reread
after_prepared_reread_before_hidden_resume
after_hidden_successor_publish_before_reread
after_hidden_reread_before_m3f
after_m3f_plan_before_m3g
after_m3g_index_before_log
after_m3g_before_control_reread
after_controls_reread_before_tombstone
during_tombstone_publish
after_tombstone_publish_before_reread
after_tombstone_reread_before_applied_receipt
after_finalization_before_return
```

The `after_tombstone_reread_before_applied_receipt` seam remains as an explicit Option-A boundary: there is no separate applied receipt. Restart returns from the tombstone. Every post-hidden fault is forward-only.

## Public-safe results

`PrimaryForgetApplyResult` and `PrimaryForgetRecoveryResult` contain only bounded status flags, lifecycle/mutation/retrieval state, prior/result revisions, and bounded reason IDs. Their `repr` and `to_log_dict` exclude reason text, title, summary, character and namespace values, memory/physical/operation IDs, token, digests, lineage, paths, timestamps, artifacts, nested M3 evidence, and raw exceptions.

## Non-goals

I-4C2 does not implement ordinary M2 lifecycle filtering, RelayCTX hidden exclusion, SOUL Lab API/UI, directory-wide recovery scanner, polling, sleep, retry loop, scheduler, daemon, worker pool, restore/unhide, physical deletion, secure erase, Pin/Unpin, Merge/Supersession, Held Apply/Discard, Secondary consolidation, or RelaySOUL mutation.

Those statements describe the I-4C2 ownership boundary. Current repository status for later I-4D/I-4E/I-4F slices belongs to [Project Status](../PROJECT_STATUS.md).

## Validation

Dedicated validation covers normal revision 1 and corrected revision N paths, prepared-only restart, hidden-only restart, index-only restart, controls-only restart, tombstone response loss, expired exact replay, different-binding conflict, concurrent-loser normalization, current-state projection, shared-lock races, strict artifact security, content leakage, I-4C1/I-4B/I-3 regressions, M3e-M3h regressions, documentation links/current-boundary checks, and `compileall`.

The dedicated workflow is:

```text
.github/workflows/phase-i4c2-primary-forget-recovery.yml
```
