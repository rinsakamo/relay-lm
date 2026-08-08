---
relaylm_doc_type: implementation_handoff
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - Primary MEM page-writer schema changes
  - M3f-M3h reconciliation ownership changes
  - page publication durability semantics change
  - RT-1 Primary writer-decision carriage changes which production calls may reach M3e
  - RT-1D-R5 or R6 retires the Primary writer path
relaylm_not_authoritative_for:
  - Phase 6 queue, dispatch, worker, or retry orchestration
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - Secondary MEM consolidation semantics
  - request-runtime wiring
  - repository-wide implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - relaymem_m3d_primary_writer_handoff.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_mvp_design.md
  - memory_lifecycle_design.md
  - relaymem_slp_current_target.md
  - ../PROJECT_STATUS.md
---
# RelayMEM-M3e Atomic Primary MEM Page Writer

Last reviewed: 2026-08-08 JST

## Status

RelayMEM-M3e remains implemented as a default-off, dry-run-first helper that can atomically publish one validated Primary MEM Markdown page.

```text
M3d exact writer-eligible handoff
  -> M3e secure store/path revalidation
  -> fsynced private temp file
  -> exclusive hard-link publication
  -> fsynced target directory
  -> runtime-private receipt + content-free projection
```

M3e writes only the page selected by M3d. It does not create directories, update `memory/mem/index.md`, append to `memory/mem/log.md`, invoke RelaySLP, mutate RelaySOUL, expose a Lab API, wire request runtime, or change visible response delivery.

Under RT-1D-R4, M3e is a retained Primary compatibility mutation component below the exact C1-1 Primary writer-decision gate. Production compose rejects a non-permitted writer decision before protected-source consumption and before any M3a-M3h stage, so a normal production invocation can reach M3e only after that upstream admission has succeeded.

M3e itself does not accept, resolve, cache, refresh, or reconstruct the RT-1 writer decision. Its mode gates, exact M3d handoff, store state, idempotency state, or previous page existence cannot grant Primary writer authority. R5/R6 own final retirement or explicitly retained historical/test disposition of this Primary page-writer surface.

## Production authorization boundary

The current retained compatibility hierarchy is:

```text
exact RT-1 Primary writer decision
  -> rejected: C1-1 stops before M3a-M3h
  -> permitted:
       M3a -> M3b -> M3c -> M3d
       -> M3e atomic page publication
       -> M3f reconciliation preflight
       -> M3g index-before-log apply
       -> M3h recovery audit
```

The writer decision is a production admission decision owned above M3e. M3e owns only the atomic page-publication mechanics for an already-admitted pipeline invocation.

Direct M3e helper tests can exercise mutation semantics with its explicit local gates. Such tests prove the M3e contract; they are not a second production cutover path and do not imply that those local gates can bypass `primary_writer_fenced`.

## Public helper

```python
apply_relaymem_primary_page_write(
    writer_handoff_artifact=...,
    root_path=...,
    enabled=False,
    dry_run_only=True,
    apply_enabled=False,
)
```

Schemas:

```text
relaymem.primary_page_write_apply.v0
relaymem.primary_page_write_receipt.v0
relaymem.primary_page_write_projection.v0
```

Actual helper publication requires all three local caller gates:

```text
enabled=true
apply_enabled=true
dry_run_only=false
```

It additionally requires one exact M3d handoff with `preflight_status=ready` and `writer_apply_eligible=true`.

These are M3e mutation-mechanics gates. They are necessary for this helper to publish a page but are not sufficient to establish current production writer authority. Under C1-1, the exact RT-1 writer decision has already been accepted before M3d/M3e can be reached.

## Revalidated M3d contract

M3e repeats the safety checks that matter at mutation time:

- exact M3d result, handoff, content-free projection, and projection-item schemas and field sets,
- rejection of unknown additive fields rather than silently accepting possible content-bearing extensions,
- helper/read-only/no-prior-side-effect flags,
- strict booleans and one-handoff cardinality,
- Primary memory kind/category correspondence,
- free-to-update / ordinary-memory policy,
- source event, candidate, namespace, lineage, and identifier shapes,
- M3b idempotency-key recomputation,
- deterministic Primary MEM target path,
- UTF-8 page bytes, byte count, and SHA-256 digest,
- exact page front-matter field set/order and metadata correspondence,
- deterministic page body,
- absence of raw message history, raw source text, and raw affect fields,
- absence of private identifiers, paths, page content, and hashes from the supplied M3d public projection.

A malformed or non-writer-eligible handoff never reaches filesystem mutation. A valid handoff proves only that M3d's page/store preflight is exact; it does not create or preserve RT-1 writer permission.

## Secure directory traversal

M3e requires an existing store root and existing Primary target directory. It never creates either.

On supported POSIX-style runtimes, the root and each target-directory component are opened one component at a time using directory file descriptors. Before and after opening each component, M3e compares non-following metadata and the opened inode. Symlink components, non-directories, missing directories, and component replacement races fail closed.

The target filename is the exact deterministic `<idempotency_key>.md` filename selected by M3d. Parent traversal, absolute paths, backslashes, non-canonical paths, Secondary MEM paths, and category substitutions are rejected.

Platforms without the required secure `dir_fd` primitives fail closed with `primary_page_writer_platform_unsupported`.

A usable root, directory, and target path are storage prerequisites only. They cannot restore a fenced Primary writer.

## Atomic no-clobber publication

M3e never writes directly to the final page name.

1. Create a random private temp file in the already-open target directory with exclusive create and mode `0600`.
2. Write the complete UTF-8 page and `fsync` the temp file.
3. Publish with an exclusive hard link from the temp inode to the final deterministic filename.
4. Verify that the final directory entry is a regular file referring to the exact temp inode.
5. `fsync` the target directory and repeat the final-entry inode verification.
6. Remove the temp link and `fsync` the directory again.

Because the final name is linked only after the complete temp file is durable, readers do not observe a partially written final page. Hard-link publication does not replace an existing target. If the final entry no longer refers to the published temp inode, M3e returns `applied_state_uncertain` with a bounded reason rather than claiming success.

If another writer wins the same idempotency race:

- an exact existing page becomes `already_applied`,
- any differing page becomes `primary_page_writer_target_conflict`.

Recognizing an already-existing exact page is a read-only idempotency check. That path sets `durability_confirmed=false` because the current invocation did not perform and verify the original publication sequence.

Idempotent convergence is a durability/consistency property, not an authorization property. An existing exact page or an `already_applied` result cannot authorize a later Primary mutation after the upstream writer fence.

## Result and failure states

Normal states:

- `disabled`
- `dry_run_ready`
- `applied`
- `already_applied`
- `blocked`

Rare post-publication states are reported explicitly rather than hidden:

- `applied_durability_unconfirmed`
- `applied_cleanup_incomplete`
- `applied_state_uncertain`

Those states may carry `writes_memory=true` and `page_applied=true` while keeping `durability_confirmed=false` or `cleanup_complete=false`. A retry is safe because the exact final page is recognized as an idempotent no-op, but any later production retry still requires writer admission at the owning C1-1/C1-2 boundary.

OS exception text, temp filenames, root paths, and page content are never copied into public diagnostics.

## Runtime-private receipt

When a dry-run target is ready, a page is applied, or an exact page already exists, M3e emits a runtime-private receipt containing the deterministic identifiers, target path, page byte count/digest, status, and durability/idempotency booleans.

The receipt omits the page Markdown and raw source/message/affect content. It is consumed by the implemented M3f reconciliation preflight and is not public diagnostics.

The receipt intentionally contains no RT-1 writer-decision identity. It records page-publication evidence, not durable authorization that can be replayed to regain mutation permission.

## Content-free projection

The public projection contains only bounded status and shape metadata:

- status,
- handoff-valid boolean,
- memory kind and target category,
- page byte count,
- write/applied/idempotent/durability/cleanup booleans,
- bounded reason identifiers.

It omits:

- store root path,
- candidate ID and namespace,
- target path,
- lineage fingerprint and idempotency key,
- page Markdown and digest,
- raw source/message/affect content,
- temp filename and OS exception details,
- private RT-1 writer-decision identity.

The projection is observability only and cannot be used to infer or recreate writer permission.

## Preserved non-goals

M3e does not:

- create missing store or category directories,
- overwrite or replace an existing page,
- update index or log files,
- reconcile an interrupted page/index/log transaction,
- wire request runtime,
- enqueue or execute RelaySLP work,
- implement Phase 6 dispatch idempotency,
- resolve or refresh RT-1 cutover state,
- grant or persist Primary writer authorization,
- mutate RelaySOUL,
- expose a Lab API,
- change visible response delivery,
- implement Secondary MEM consolidation.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_primary_page_writer.py \
  relaylm/_relaymem_primary_page_writer_common.py \
  relaylm/_relaymem_primary_page_writer_handoff.py \
  relaylm/_relaymem_primary_page_writer_contract.py \
  relaylm/_relaymem_primary_page_writer_io.py \
  relaylm/_relaymem_primary_page_writer_impl.py \
  scripts/relaylm_relaymem_primary_page_writer_smoke.py \
  scripts/relaylm_relaymem_primary_page_writer_security_smoke.py \
  scripts/relaylm_relaymem_primary_page_writer_atomicity_smoke.py

PYTHONPATH=. python scripts/relaylm_relaymem_primary_page_writer_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_page_writer_security_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_page_writer_atomicity_smoke.py
```

Coverage includes default-off behavior, dry-run, successful publication, repeat no-op, existing-page conflict, forged idempotency, path traversal, exact field-set rejection, raw-content rejection, strict booleans, projection leakage, root/parent/target symlinks, missing directories, concurrent same-key writers, final-entry inode verification, no partial final page, and temp cleanup after pre-publication failure.

The current C1-1/C1-2 worker regression umbrella separately proves writer-decision rejection before M3e is reached. M3e's dedicated smokes remain page-writer contract/security/atomicity tests rather than cutover-authority tests.

## Current downstream boundary

M3e is no longer waiting for a later reconciliation slice. Its exact durable receipt feeds the implemented M3f-M3h owners:

```text
M3e exact page receipt
  -> M3f Primary MEM index/log reconciliation preflight
  -> M3g Primary MEM index/log reconciliation apply
  -> M3h Primary MEM reconciliation recovery audit
```

M3e owns atomic page publication and its durability/idempotency evidence. M3f owns deterministic reconciliation planning, M3g owns index-before-log mutation, and M3h owns read-only recovery classification. Phase 6 queue/dispatch/worker work remains a separate authority and does not reuse RelayMEM memory-write idempotency as dispatch permission.

All of these retained Primary persistence capabilities remain subordinate to the exact upstream RT-1 writer decision in production. R5/R6 own their final retirement or explicitly retained historical/read-only/test disposition. This handoff does not pre-authorize deletion, weaken atomicity, or move Primary mutation semantics to another owner.
