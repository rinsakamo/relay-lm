---
relaylm_doc_type: implementation_handoff
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - M3g reconciliation receipt schema changes
  - M3h recovery classification changes
  - journaled recovery or repair apply lands
  - RT-1 Primary writer-decision carriage changes the meaning of a later retry/repair
  - RT-1D-R5 or R6 retires the Primary writer path
relaylm_not_authoritative_for:
  - Phase 6 queue, dispatch, worker, or retry orchestration
  - request-runtime wiring
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - journaled recovery or repair authorization
  - Secondary MEM consolidation
  - SOUL Lab memory operation APIs
  - repository-wide implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - relaymem_mvp_implementation_plan.md
  - memory_lifecycle_design.md
  - relaymem_slp_current_target.md
  - ../PROJECT_STATUS.md
---
# RelayMEM-M3h Primary MEM Index/Log Reconciliation Recovery Audit

Last reviewed: 2026-08-08 JST

## Status

RelayMEM-M3h remains implemented as a default-off, dry-run-only, read-only, helper-only recovery audit boundary.

It directly consumes one exact runtime-private M3g receipt and compares that receipt with the current durable Primary MEM page, `memory/mem/index.md`, and `memory/mem/log.md`.

```text
exact M3g runtime-private receipt
  + securely revalidated current store
  -> bounded current-store state
  -> recovery classification
  -> runtime-private audit
  -> content-free public projection
```

M3h never repairs the store. It does not create a journal, replace a file, remove a temporary artifact, or invoke another runtime component.

Under RT-1D-R4, M3h is a retained Primary compatibility audit below the exact writer-decision-controlled production pipeline. It is read-only and does not itself require or resolve writer permission merely to inspect exact historical/current M3g evidence. However, any later production retry, M3g apply, or future repair mutation remains independently subject to the owning RT-1 writer-decision gate.

M3h does not accept, resolve, cache, refresh, serialize, or reconstruct the RT-1 writer decision. Its current-store state, recovery classification, shared-lock acquisition, exact M3g receipt, or cleanup-artifact observation cannot grant or preserve Primary writer authority.

R5/R6 own final retirement or explicitly retained historical/read-only/test disposition of this Primary recovery-audit surface. A future journaled repair apply, if ever required, must remain a separate explicit authority.

## Authorization and recovery boundary

The current retained compatibility hierarchy is:

```text
production Primary mutation
  -> exact RT-1 writer decision must permit
  -> C1-1 M3a ... M3g mutation
  -> M3h read-only audit may classify resulting durable state

later retry or repair mutation
  -> must enter through its owning current writer-authority gate
  -> M3h classification alone never authorizes mutation
```

M3h is therefore evidence/classification authority, not mutation authority. A classification can say that retry or stronger recovery evidence is appropriate, but it cannot mint a writer token, refresh cutover state, or bypass `primary_writer_fenced`.

Direct M3h helper tests may audit exact receipts and store states independently. Those calls prove read-only recovery classification/security semantics, not current Primary writer availability.

## Public helper

```python
audit_relaymem_primary_index_log_reconciliation_recovery(
    receipt=...,
    root_path=...,
    enabled=False,
    dry_run_only=True,
)
```

Schemas:

```text
relaymem.primary_index_log_reconciliation_recovery_audit_result.v0
relaymem.primary_index_log_reconciliation_recovery_audit.v0
relaymem.primary_index_log_reconciliation_recovery_projection.v0
```

The supported execution gate is exact:

```text
enabled=true
dry_run_only=true
```

Any non-boolean gate or `dry_run_only=false` is blocked. The default call is inert.

These local gates enable a read-only audit only. They do not establish writer permission or repair authority.

## Exact M3g receipt consumption

M3h accepts only the exact field set of:

```text
relaymem.primary_index_log_reconciliation_receipt.v0
```

The validator rechecks:

- `runtime_private=true` and `content_included=false`,
- the bounded M3g reconciliation state and result status,
- deterministic page path and SHA-256-shaped identities/digests,
- strict booleans and integer operation count,
- operation-count correspondence with the reconciliation state,
- index/log update aliases,
- write/update/no-op consistency,
- expected/proposed digest transition consistency,
- durability and cleanup claims,
- status-specific receipt invariants.

Unknown fields, boolean-as-integer values, parent-relative paths, malformed identities, and contradictory receipt claims fail closed before store inspection.

M3h does not accept the M3g public projection as a substitute for the runtime-private receipt.

An exact receipt is mutation evidence from an earlier M3g invocation. It intentionally contains no RT-1 writer-decision identity and cannot be replayed as authorization for another mutation.

## Secure read-only store audit

M3h reuses the M3f secure directory-FD traversal and bounded regular-file read helpers. It opens the configured store root without following symlinks, securely traverses the fixed memory directories, and takes a non-blocking shared advisory lock on `memory/mem` for the complete audit.

The audit fails closed on:

- unsupported secure POSIX primitives,
- missing or invalid root/directory components,
- path traversal or substituted page path,
- symlinked or non-regular page/control files,
- lock contention,
- oversized content,
- malformed UTF-8,
- digest drift,
- malformed marker contracts,
- page/index/log scope or identity mismatch.

M3h performs no open-for-write operation.

The shared advisory lock establishes a read-consistency/concurrency boundary for the audit. It is not semantic writer authority, and acquiring it cannot authorize a future M3g or repair mutation.

## Primary page revalidation

The current Primary MEM page is rechecked against the receipt and current page contract:

- exact page SHA-256 digest,
- exact Primary page schema,
- `memory_layer=primary`,
- free-to-update promotion policy,
- ordinary-memory safety scope,
- exact memory-write idempotency key,
- deterministic memory-kind directory binding,
- bounded title and summary,
- deterministic page body.

The page result is exposed publicly only as a boolean verification outcome. The path, digest, title, summary, namespace, and page body remain runtime-private or absent.

A valid durable page is evidence for classification only. Store validity does not restore a Primary writer after the owning cutover state has fenced it.

## Index/log revalidation

For both control files, M3h computes the current digest and classifies it against the receipt as:

```text
expected
proposed
diverged
missing
invalid
```

It then reparses every canonical compact JSON marker, revalidates the target marker identity, and checks the page path, memory layer, idempotency key, page digest, and log-to-index linkage.

When target markers are present, M3h also cross-checks page, index, and log scope fields such as memory kind, namespace, source event kind, promotion policy, safety scope, and target category.

## Current-store states

The read-only store audit produces one bounded state:

```text
fully_reconciled
index_applied_log_pending
not_applied
log_applied_index_pending
page_unverified
control_unverified
state_diverged
not_evaluated
```

`index_applied_log_pending` is the supported M3g intermediate state: the index equals the planned proposed state while the log remains at the planned expected state.

`log_applied_index_pending` is observable but is not a valid M3g apply order. For an ordinary dry-run receipt it means no recovery action was initiated. For an apply/uncertain receipt it requires manual or future journaled handling.

These store states classify durable evidence only. None is an RT-1 writer-decision state.

## Recovery classifications

M3h returns one content-free classification:

```text
recovery_not_required
retry_reconciliation
manual_confirmation_required
journaled_recovery_candidate
not_evaluated
```

### `recovery_not_required`

Used when the current state is already fully reconciled under an ordinary successful receipt, or when a dry-run/blocked receipt still corresponds to an unchanged non-applied store.

This means no M3h-identified recovery work is required. It does not assert anything about current Primary writer permission.

### `retry_reconciliation`

Used only for a verified `index_applied_log_pending` store. Retrying still requires either:

- the same exact M3f plan retained by the caller, or
- a freshly generated M3f `log_update_required` plan.

The M3g receipt does not contain proposed control-file content and cannot itself drive repair.

This classification says that reconciliation evidence is safely retryable. It does not authorize that retry. A later production M3g invocation still requires the exact upstream writer decision to permit mutation.

### `manual_confirmation_required`

Used when current files are fully reconciled but an M3g durability claim remains unconfirmed, or when a non-journaled state does not safely imply a retry.

Manual confirmation is an operational/evidence requirement, not a path around the writer fence.

### `journaled_recovery_candidate`

Used for cleanup-incomplete or state-uncertain outcomes, uncertain partial/divergent states, or bounded evidence that a future journal-aware recovery design may be needed.

This classification does not create a journal and does not authorize repair. Any future repair apply would need its own explicit mutation contract and current writer-authorization boundary.

## Cleanup-artifact observation

M3h performs one bounded directory listing and counts names that exactly match the private M3g temporary-name pattern for the receipt's deterministic entry identities.

This is name-only diagnostics. M3h does not open, follow, remove, rename, or rely on the contents of those names. Directory-entry count is bounded, and only the aggregate presence/count enters the runtime-private audit. The public projection contains only a boolean presence flag.

Cleanup-artifact presence is diagnostic evidence only and cannot trigger or authorize mutation from M3h.

## Runtime-private audit

The runtime-private audit may contain:

- source M3g status and reconciliation state,
- page relative path and digest,
- memory-write idempotency key,
- index/log entry identities,
- current page/index/log/store states,
- cleanup-artifact count,
- recovery classification,
- whether retry requires an exact retained plan or fresh preflight.

It never includes page, index, or log text content.

The audit intentionally contains no RT-1 writer-decision identity. It is durable-state interpretation for the current inspection, not a transferable authorization artifact.

## Content-free public projection

The public projection is restricted to:

- bounded result/source/store state identifiers,
- receipt-valid and page-verified booleans,
- index/log state identifiers,
- cleanup-artifact presence boolean,
- recovery classification booleans,
- bounded reason identifiers,
- explicit no-write booleans.

It does not contain:

- store root or relative paths,
- namespace,
- idempotency key,
- page/control-file digests,
- marker entry identities,
- page/index/log content,
- OS exception strings,
- private RT-1 writer-decision identity.

The projection is observability only and cannot be used to infer or reconstruct writer permission.

## Preserved non-goals

M3h does not:

- repair page, index, or log,
- create or replay a journal,
- remove cleanup artifacts,
- regenerate an M3f plan,
- invoke M3g apply,
- claim page/index/log transactionality,
- wire request runtime,
- enqueue or execute RelaySLP jobs,
- resolve or refresh RT-1 cutover state,
- grant or persist Primary writer authorization,
- mutate RelaySOUL,
- process Secondary MEM,
- expose a SOUL Lab API,
- change visible response delivery.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_primary_index_log_recovery_audit.py \
  relaylm/_relaymem_primary_index_log_recovery_audit.py \
  relaylm/_relaymem_primary_index_log_recovery_audit_contract.py \
  relaylm/_relaymem_primary_index_log_recovery_audit_io.py \
  relaylm/_relaymem_primary_index_log_recovery_audit_io_page.py \
  relaylm/_relaymem_primary_index_log_recovery_audit_io_control.py \
  relaylm/_relaymem_primary_index_log_recovery_audit_io_cleanup.py \
  scripts/relaylm_relaymem_primary_index_log_recovery_audit_smoke.py \
  scripts/relaylm_relaymem_primary_index_log_recovery_audit_security_smoke.py

PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_recovery_audit_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_recovery_audit_security_smoke.py
```

Coverage includes default-off behavior, successful full reconciliation, durability uncertainty, content-free projection, exact receipt rejection, invalid dry-run gates, traversal rejection, advisory-lock contention, and control-file symlink rejection.

The current C1-1/C1-2 regression umbrella separately proves that a non-permitted writer decision stops before M3g mutation is reached. M3h's dedicated smokes remain read-only audit/classification/security tests rather than cutover-authority tests.

## Downstream boundary

M3h is the implemented read-only end of the current M3a-M3h Primary persistence/reconciliation chain. It can classify whether no recovery is needed, bounded reconciliation retry is evidence-supported, manual confirmation is required, or a future journal-aware design may be appropriate.

A later slice may introduce journaled recovery only if operational evidence requires it. That work must define a new durable journal, explicit apply contract, and current writer-authorization gate rather than treating this read-only classifier as repair authority.

Request-runtime, Phase 6 worker, RelaySLP, RelaySOUL, Secondary MEM, and SOUL Lab integration remain separate tracks. All retained Primary persistence/reconciliation capabilities remain subordinate to the exact RT-1 decisions in production, and R5/R6 own final retirement or explicitly retained historical/read-only/test disposition.
