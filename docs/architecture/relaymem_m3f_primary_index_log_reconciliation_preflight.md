---
relaylm_doc_type: implementation_handoff
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - Primary MEM index or log entry schema changes
  - M3g reconciliation apply lands
  - M3e receipt semantics change
relaylm_not_authoritative_for:
  - Phase 6 queue, dispatch, worker, or retry orchestration
  - request-runtime wiring
  - Secondary MEM consolidation
  - repository-wide implementation status
relaylm_related_authority:
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_mvp_design.md
  - memory_lifecycle_design.md
  - relaymem_slp_current_target.md
---
# RelayMEM-M3f Primary MEM Index/Log Reconciliation Preflight

## Status

RelayMEM-M3f is implemented as a default-off, read-only, dry-run-only helper that consumes one exact M3e page-write receipt, revalidates the published Primary MEM page, inspects the current index and log, and emits a deterministic reconciliation plan.

```text
exact eligible M3e receipt
  + verified published Primary MEM page
  + bounded current memory/mem/index.md
  + bounded current memory/mem/log.md
  -> runtime-private ordered reconciliation plan
  -> content-free public projection
```

M3f never writes the index, log, page, journal, queue, trace, or visible response.

## Public helper

```python
build_relaymem_primary_index_log_reconciliation_preflight(
    receipt=...,
    root_path=...,
    enabled=False,
    dry_run_only=True,
)
```

Schemas:

```text
relaymem.primary_index_log_reconciliation_preflight.v0
relaymem.primary_index_log_reconciliation_plan.v0
relaymem.primary_index_log_reconciliation_projection.v0
relaymem.primary_index_entry.v0
relaymem.primary_log_entry.v0
```

The helper produces a plan only when `enabled=true` and `dry_run_only=true`. Passing a non-boolean gate or requesting a non-dry-run mode fails closed.

## Eligible M3e receipts

The receipt must have the exact `relaymem.primary_page_write_receipt.v0` field set and remain runtime-private/content-free. M3f requires:

- Primary MEM,
- `promotion_policy=free_to_update`,
- `safety_scope=ordinary_memory`,
- a supported source-event and Primary memory-kind/category pair,
- a deterministic Primary target path,
- a valid page byte count and SHA-256 digest,
- the exact recomputed M3b memory-write idempotency key,
- `updates_index=false` and `updates_log=false`,
- complete cleanup.

Normal eligibility is:

```text
status=applied
writes_memory=true
page_applied=true
idempotent_noop=false
durability_confirmed=true
```

`already_applied` is also accepted only with the exact M3e no-op booleans. It does not inherit a durability claim from the receipt. The current page must pass the full M3f page revalidation before reconciliation is eligible.

Post-publication uncertainty states, dry-run-ready receipts, unknown fields, boolean-as-integer values, and malformed identifiers fail closed.

## Read-only store validation

M3f securely reopens:

```text
store root
M3e target Primary MEM page
memory/mem/index.md
memory/mem/log.md
```

The root and directory components are traversed with directory file descriptors on supported POSIX runtimes. Symlink components, non-directories, regular-file substitutions, inode changes during read, traversal, absolute paths, backslashes, and category substitutions are rejected.

Read bounds are:

```text
Primary page: 8 KiB
index.md: 64 KiB
log.md: 64 KiB
marker count per control file: 256
marker line: 4 KiB
```

All three files must be regular UTF-8 files. OS exception strings and absolute root paths are not copied into diagnostics.

## Page revalidation

The receipt is not treated as proof that the page still exists. M3f verifies:

- the exact deterministic Primary path,
- regular-file and no-symlink status,
- exact byte count,
- exact SHA-256 digest,
- exact Primary page front-matter key set and order,
- page schema and Primary memory layer,
- memory kind, source event, namespace, lineage, and idempotency correspondence,
- free-to-update / ordinary-memory policy,
- summary/title bounds,
- deterministic body structure.

Missing and mismatching pages are reported separately as `page_missing` and `page_mismatch`.

## Deterministic index plan

The existing file content is preserved byte-for-byte. When the page is not indexed, M3f proposes one canonical append marker:

```text
<!-- relaymem-primary-index-entry-v0 {canonical compact JSON} -->
```

The private entry contains:

- deterministic entry identity,
- page-relative path,
- Primary memory layer,
- memory kind and target category,
- namespace, source-event kind, promotion policy, and safety scope,
- memory-write idempotency key,
- page digest.

The operation includes the expected current byte count/digest and the proposed next content, byte count, and digest. This gives M3g a compare-and-swap input without allowing M3f to mutate the file.

An exact existing entry is an idempotent no-op. Every recognized marker, including unrelated entries, must use canonical compact JSON and pass exact field-set, scope, path, digest, and recomputed deterministic entry-ID validation. Duplicate identities, a reused page path or idempotency key with different content, malformed or non-canonical markers, unknown marker fields, or schema/value mismatches are `index_conflict`.

## Deterministic log plan

The log uses the same bounded append-marker model:

```text
<!-- relaymem-primary-log-entry-v0 {canonical compact JSON} -->
```

The deterministic log identity binds the page path, page digest, and memory-write idempotency key. The entry also references the deterministic index entry identity, preserves namespace/safety/source lineage metadata, and records `operation=primary_page_published`.

Repeated runs recognize an exact entry as a no-op. Every recognized log marker must also revalidate its deterministic log ID, linked index entry ID, lineage hash, operation kind, path, scope, and canonical JSON. Duplicate or conflicting identities, malformed or non-canonical markers, and schema/field/value drift are `log_conflict`.

## Reconciliation states and ordering

M3f exposes an operation-specific reconciliation state plus `preflight_status=ready|blocked`.

```text
index_and_log_update_required
  ordered operations: index append, then log append

log_update_required
  exact index exists; append log only

index_update_required
  exact log exists but index is missing; verified page remains source of truth,
  so repair the index without duplicating the exact log entry

already_reconciled
  both exact entries exist; zero operations

page_missing
page_mismatch
index_conflict
log_conflict
blocked
```

A log-only exact state is repairable because M3f independently verifies the durable page and the exact log identity. A conflicting log is never used as proof of page validity.

Missing `index.md` or `log.md` files are blocked in M3f. File creation policy belongs to the later apply slice.

## Runtime-private plan

The private plan may contain:

- page and control-file relative paths,
- page and control-file digests,
- memory-write idempotency and entry identities,
- expected current file state,
- proposed complete next content,
- ordered operation list.

It always reports:

```text
writes_memory=false
updates_index=false
updates_log=false
```

The memory-write idempotency key remains distinct from Phase 6 dispatch idempotency.

## Content-free projection

The public projection contains only:

- reconciliation and preflight status,
- receipt-valid and page-verified booleans,
- memory kind and target category,
- index/log update-required booleans,
- bounded conflict and operation counts,
- bounded reason identifiers,
- no-write booleans.

It does not contain:

- store root or target/control-file paths,
- namespace or candidate ID,
- lineage or idempotency identifiers,
- page/control-file digests,
- page, index, or log content,
- proposed mutation content,
- OS exception text.

## Preserved non-goals

M3f does not:

- write or create index/log files,
- update the published page,
- provide an atomic page/index/log transaction,
- create a journal,
- perform crash recovery,
- wire request runtime,
- enqueue or execute RelaySLP jobs,
- reuse Phase 6 dispatch idempotency,
- mutate RelaySOUL,
- process Secondary MEM,
- expose a Lab API,
- change visible response delivery.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_primary_index_log_reconciliation.py \
  relaylm/_relaymem_primary_index_log_reconciliation.py \
  relaylm/_relaymem_primary_index_log_reconciliation_contract.py \
  relaylm/_relaymem_primary_index_log_reconciliation_io.py \
  relaylm/_relaymem_primary_index_log_reconciliation_plan.py \
  scripts/relaylm_relaymem_primary_index_log_reconciliation_smoke.py \
  scripts/relaylm_relaymem_primary_index_log_reconciliation_marker_smoke.py

PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_reconciliation_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_reconciliation_marker_smoke.py
```

Coverage includes default-off behavior, dry-run gating, exact receipt validation, strict integers, page byte/digest/front-matter revalidation, both-missing/index-only/log-only/already-reconciled states, deterministic ordering, target and unrelated-entry conflict detection, non-canonical/malformed marker rejection, content-free projection, missing page, bounds, and symlink rejection.

## Next bounded slice

The next independent persistence slice should be:

```text
RelayMEM-M3g Primary MEM index/log reconciliation apply
  -> consume one exact M3f plan
  -> revalidate expected current digests
  -> apply index before log
  -> define atomicity, interrupted-apply, and retry semantics
  -> emit a runtime-private receipt and content-free projection
```

Crash recovery and page/index/log transaction journaling should remain explicit rather than being implied by M3g.
