---
relaylm_doc_type: implementation_handoff
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - Primary MEM index or log entry schema changes
  - M3g or M3h reconciliation semantics change
  - M3e receipt semantics change
  - RT-1 Primary writer-decision carriage changes which production calls may reach M3f
  - RT-1D-R5 or R6 retires the Primary writer path
relaylm_not_authoritative_for:
  - Phase 6 queue, dispatch, worker, or retry orchestration
  - request-runtime wiring
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - Secondary MEM consolidation
  - repository-wide implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - memory/formation.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - project_execution_plan.md
  - relaymem_mvp_design.md
  - memory_lifecycle_design.md
  - relaymem_slp_current_target.md
  - ../PROJECT_STATUS.md
---
# RelayMEM-M3f Primary MEM Index/Log Reconciliation Preflight

Last reviewed: 2026-08-08 JST

## Status

RelayMEM-M3f remains implemented as a default-off, read-only, dry-run-only helper that consumes one exact M3e page-write receipt, revalidates the published Primary MEM page, inspects the current index and log, and emits a deterministic reconciliation plan.

```text
exact eligible M3e receipt
  + verified published Primary MEM page
  + bounded current memory/mem/index.md
  + bounded current memory/mem/log.md
  -> runtime-private ordered reconciliation plan
  -> content-free public projection
```

M3f never writes the index, log, page, journal, queue, trace, or visible response.

Under RT-1D-R4, M3f is a retained Primary compatibility preflight below the exact C1-1 Primary writer-decision gate. Production compose rejects a non-permitted writer decision before any M3a-M3h stage. M3f therefore plans reconciliation only for an already-admitted production pipeline invocation.

M3f itself does not accept, resolve, cache, refresh, or reconstruct the RT-1 writer decision. A valid M3e receipt, verified page, `plan_ready`, repairable reconciliation state, or `already_reconciled` result is storage/reconciliation evidence only and cannot grant or preserve Primary writer authority.

M3g apply and M3h recovery audit are now implemented downstream. R5/R6 own final retirement or explicitly retained historical/read-only/test disposition of this Primary reconciliation preflight.

## Production authorization boundary

The current retained compatibility hierarchy is:

```text
exact RT-1 Primary writer decision
  -> rejected: C1-1 stops before M3a-M3h
  -> permitted:
       M3a -> M3b -> M3c -> M3d -> M3e
       -> M3f reconciliation preflight       read-only
       -> M3g reconciliation apply           mutation
       -> M3h recovery audit                 read-only
```

The writer decision is owned above M3f. M3f owns deterministic current-store inspection and planning only. Its output is a compare-and-swap plan for M3g, not a durable authorization token.

Direct helper tests may exercise M3f independently with exact historical/current artifacts. Such calls prove plan, conflict, and security semantics; they do not create a second production writer-admission path or bypass `primary_writer_fenced`.

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

These local gates govern read-only M3f execution only. They do not establish RT-1 writer permission.

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

An eligible receipt proves exact page-publication evidence for reconciliation. It does not prove that a later production invocation still has Primary writer permission.

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

All three files must be regular UTF-8 files. The control files must retain their exact first-line base headings, `# Index` and `# Log`; a missing or substituted heading is a conflict. OS exception strings and absolute root paths are not copied into diagnostics.

Valid store state is a planning prerequisite, not writer authorization. Store presence or an existing exact Primary page cannot revive a fenced writer.

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

An exact existing entry is an idempotent no-op. Every recognized marker, including unrelated entries, must use canonical compact JSON and pass exact field-set, scope, path, digest, and recomputed deterministic entry-ID validation. Duplicate identities, a reused page path or idempotency key with different content, malformed or non-canonical markers, markers from another control-file family, unknown marker versions or fields, or schema/value mismatches are `index_conflict`.

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

Missing `index.md` or `log.md` files are blocked in M3f. File creation policy belongs to the M3g apply owner and its accepted contract; M3f itself does not create control files.

`preflight_status=ready`, repairability, and `already_reconciled` describe reconciliation state only. They do not authorize M3g or any later Primary mutation when the production writer decision is rejected.

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

The plan intentionally contains no RT-1 writer-decision identity. It records exact reconciliation intent for an already-admitted pipeline invocation and cannot be replayed as permission in another invocation.

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
- OS exception text,
- private RT-1 writer-decision identity.

The public projection is observability only and cannot be used to infer or reconstruct writer permission.

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
- resolve or refresh RT-1 cutover state,
- grant or persist Primary writer authorization,
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

The current C1-1/C1-2 regression umbrella separately proves that a non-permitted writer decision stops before M3f is reached. M3f's dedicated smokes remain read-only reconciliation/marker/security tests rather than cutover-authority tests.

## Current downstream boundary

M3f is no longer waiting for a later apply slice. Its exact runtime-private plan feeds the implemented M3g apply owner, whose receipt in turn feeds M3h:

```text
M3f exact reconciliation plan
  -> M3g Primary MEM index/log reconciliation apply
  -> M3h Primary MEM reconciliation recovery audit
```

M3f owns deterministic read-only planning and conflict detection. M3g owns index-before-log mutation, revalidation, durability, and interrupted-apply semantics. M3h owns read-only recovery classification and does not itself repair the store.

All of these retained Primary reconciliation capabilities remain subordinate to the exact upstream RT-1 writer decision in production. R5/R6 own final retirement or explicitly retained historical/read-only/test disposition. This handoff does not pre-authorize deletion, weaken conflict detection, or move mutation/recovery semantics to another owner.
