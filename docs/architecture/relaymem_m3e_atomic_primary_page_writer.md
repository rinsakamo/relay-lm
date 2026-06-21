---
relaylm_doc_type: implementation_handoff
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - Primary MEM page-writer schema changes
  - index/log reconciliation lands
  - page publication durability semantics change
relaylm_not_authoritative_for:
  - Phase 6 queue, dispatch, worker, or retry orchestration
  - Secondary MEM consolidation semantics
  - request-runtime wiring
  - repository-wide implementation status
relaylm_related_authority:
  - relaymem_m3d_primary_writer_handoff.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_mvp_design.md
  - memory_lifecycle_design.md
  - relaymem_slp_current_target.md
---
# RelayMEM-M3e Atomic Primary MEM Page Writer

## Status

RelayMEM-M3e is implemented as a default-off, dry-run-first helper that can atomically publish one validated Primary MEM Markdown page.

```text
M3d exact writer-eligible handoff
  -> M3e secure store/path revalidation
  -> fsynced private temp file
  -> exclusive hard-link publication
  -> fsynced target directory
  -> runtime-private receipt + content-free projection
```

M3e writes only the page selected by M3d. It does not create directories, update `memory/mem/index.md`, append to `memory/mem/log.md`, invoke RelaySLP, mutate RelaySOUL, expose a Lab API, wire request runtime, or change visible response delivery.

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

Actual publication requires all three caller gates:

```text
enabled=true
apply_enabled=true
dry_run_only=false
```

It additionally requires one exact M3d handoff with `preflight_status=ready` and `writer_apply_eligible=true`.

## Revalidated M3d contract

M3e repeats the safety checks that matter at mutation time:

- exact M3d result, handoff, and content-free projection schemas,
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

A malformed or non-writer-eligible handoff never reaches filesystem mutation.

## Secure directory traversal

M3e requires an existing store root and existing Primary target directory. It never creates either.

On supported POSIX-style runtimes, the root and each target-directory component are opened one component at a time using directory file descriptors. Before and after opening each component, M3e compares non-following metadata and the opened inode. Symlink components, non-directories, missing directories, and component replacement races fail closed.

The target filename is the exact deterministic `<idempotency_key>.md` filename selected by M3d. Parent traversal, absolute paths, backslashes, non-canonical paths, Secondary MEM paths, and category substitutions are rejected.

Platforms without the required secure `dir_fd` primitives fail closed with `primary_page_writer_platform_unsupported`.

## Atomic no-clobber publication

M3e never writes directly to the final page name.

1. Create a random private temp file in the already-open target directory with exclusive create and mode `0600`.
2. Write the complete UTF-8 page and `fsync` the temp file.
3. Publish with an exclusive hard link from the temp inode to the final deterministic filename.
4. `fsync` the target directory.
5. Remove the temp link and `fsync` the directory again.

Because the final name is linked only after the complete temp file is durable, readers do not observe a partially written final page. Hard-link publication does not replace an existing target.

If another writer wins the same idempotency race:

- an exact existing page becomes `already_applied`,
- any differing page becomes `primary_page_writer_target_conflict`.

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

Those states may carry `writes_memory=true` and `page_applied=true` while keeping `durability_confirmed=false` or `cleanup_complete=false`. A retry is safe because the exact final page is recognized as an idempotent no-op.

OS exception text, temp filenames, root paths, and page content are never copied into public diagnostics.

## Runtime-private receipt

When a dry-run target is ready, a page is applied, or an exact page already exists, M3e emits a runtime-private receipt containing the deterministic identifiers, target path, page byte count/digest, status, and durability/idempotency booleans.

The receipt omits the page Markdown and raw source/message/affect content. It is intended for a later index/log reconciliation slice, not public diagnostics.

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
- temp filename and OS exception details.

## Preserved non-goals

M3e does not:

- create missing store or category directories,
- overwrite or replace an existing page,
- update index or log files,
- reconcile an interrupted page/index/log transaction,
- wire request runtime,
- enqueue or execute RelaySLP work,
- implement Phase 6 dispatch idempotency,
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

Coverage includes default-off behavior, dry-run, successful publication, repeat no-op, existing-page conflict, forged idempotency, path traversal, raw-content rejection, strict booleans, projection leakage, root/parent/target symlinks, missing directories, concurrent same-key writers, no partial final page, and temp cleanup after pre-publication failure.

## Next bounded slice

The next independent RelayMEM persistence slice should consume only an exact durable M3e receipt:

```text
M3f Primary MEM index/log reconciliation preflight
  -> validate page receipt and current store state
  -> derive deterministic index/log mutation plan
  -> helper-only / dry-run-first
  -> no mutation in the first reconciliation slice
```

Actual index/log apply should remain separate until its atomicity, crash recovery, and repeated-run contract is explicit. Phase 6 queue/dispatch/worker work remains a separate track and must not reuse the RelayMEM memory-write idempotency key.
