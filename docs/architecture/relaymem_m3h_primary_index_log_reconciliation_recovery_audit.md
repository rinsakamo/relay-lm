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
relaylm_not_authoritative_for:
  - Phase 6 queue, dispatch, worker, or retry orchestration
  - request-runtime wiring
  - Secondary MEM consolidation
  - SOUL Lab memory operation APIs
  - repository-wide implementation status
relaylm_related_authority:
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_mvp_implementation_plan.md
  - memory_lifecycle_design.md
---
# RelayMEM-M3h Primary MEM Index/Log Reconciliation Recovery Audit

## Status

RelayMEM-M3h is implemented as a default-off, dry-run-only, read-only, helper-only recovery audit boundary.

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

### `retry_reconciliation`

Used only for a verified `index_applied_log_pending` store. Retrying still requires either:

- the same exact M3f plan retained by the caller, or
- a freshly generated M3f `log_update_required` plan.

The M3g receipt does not contain proposed control-file content and cannot itself drive repair.

### `manual_confirmation_required`

Used when current files are fully reconciled but an M3g durability claim remains unconfirmed, or when a non-journaled state does not safely imply a retry.

### `journaled_recovery_candidate`

Used for cleanup-incomplete or state-uncertain outcomes, uncertain partial/divergent states, or bounded evidence that a future journal-aware recovery design may be needed.

This classification does not create a journal and does not authorize repair.

## Cleanup-artifact observation

M3h performs one bounded directory listing and counts names that exactly match the private M3g temporary-name pattern for the receipt's deterministic entry identities.

This is name-only diagnostics. M3h does not open, follow, remove, rename, or rely on the contents of those names. Directory-entry count is bounded, and only the aggregate presence/count enters the runtime-private audit. The public projection contains only a boolean presence flag.

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
- OS exception strings.

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

## Downstream boundary

A later slice may introduce journaled recovery only if operational evidence requires it. That work must define a new durable journal and explicit apply contract rather than treating this read-only classifier as repair authority.

Request-runtime, Phase 6 worker, RelaySLP, RelaySOUL, Secondary MEM, and SOUL Lab integration remain separate tracks.
