---
relaylm_doc_type: implementation_handoff
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - Primary MEM writer handoff schema changes
  - durable Primary MEM filesystem apply lands
  - page/index/log persistence ownership changes
relaylm_not_authoritative_for:
  - Phase 6 queue worker retry orchestration
  - request-runtime RelaySLP admission or enqueue wiring
  - Secondary MEM consolidation semantics
  - repository-wide implementation status
relaylm_related_authority:
  - relaymem_mvp_implementation_plan.md
  - relaymem_mvp_design.md
  - memory_lifecycle_design.md
  - pipeline_implementation_plan.md
  - relaymem_slp_current_target.md
  - ../PROJECT_STATUS.md
---
# RelayMEM-M3d Primary Writer Handoff Preflight

## Status

RelayMEM-M3d is implemented as a helper-only, read-only Primary MEM writer-handoff preflight.

It consumes the exact RelayMEM-M3c Primary MEM page-candidate artifact, revalidates the candidate and configured store target, and emits one bounded runtime-private writer handoff plus a content-free projection.

M3d does not perform a filesystem write. Durable page creation, index/log mutation, and request-runtime or worker wiring remain later bounded slices.

## Why this slice stops before write apply

The current `relaymem_store.py` boundary is read-only store discovery, bounded page reading, snippet extraction, and layout diagnostics. It does not define an atomic Primary MEM writer.

The global Phase 6 plan separately reserves later page/index/log persistence orchestration and reconciliation. Therefore M3d establishes the RelayMEM-owned write semantics and target preflight without prematurely combining them with queue/worker orchestration or durable mutation.

```text
M3c validated Primary MEM page candidate
  -> M3d writer-handoff preflight
  -> later atomic Primary MEM writer
  -> later index/log reconciliation
```

## Implemented contract

Public helper:

```python
build_relaymem_primary_writer_handoff_preflight(
    page_candidate_artifact=...,
    root_path=...,
    enabled=False,
    dry_run_only=True,
    apply_enabled=False,
)
```

Schemas:

```text
relaymem.primary_writer_handoff_preflight.v0
relaymem.primary_writer_handoff.v0
relaymem.primary_writer_handoff_projection.v0
```

The helper is default-off and dry-run-first. Even when all apply-preflight gates pass, it sets `write_apply_supported=false`, `apply_allowed=false`, and `writes_memory=false`.

## Exact M3c revalidation

M3d revalidates:

- exact M3c result and page-candidate schemas,
- helper/read-only/no-side-effect flags,
- candidate cardinality and status,
- strict boolean fields,
- Primary memory layer, memory kind, target category, promotion policy, and safety scope,
- namespace, lineage fingerprint, and idempotency key shape,
- deterministic Primary MEM target path,
- UTF-8 page encoding and bounded page size,
- page byte count and SHA-256 digest,
- deterministic front-matter field set and order,
- page metadata correspondence with the candidate,
- deterministic page body and summary character count,
- upstream M3c writer-handoff eligibility when M3d apply preflight is requested.

Arbitrary upstream blocked reasons are not copied into the M3d public projection. They collapse to bounded M3d reason identifiers.

## Store-target preflight

The configured store root is inspected without mutation.

M3d requires:

- an existing non-symlink store root,
- an existing non-symlink target parent directory,
- a target path under `memory/mem/primary/`,
- the exact target category directory selected by M3c,
- no absolute path, parent traversal, backslash path, or non-canonical path,
- no symlink component or symlink target.

When the target page is absent, the handoff status is `ready`.

When the target page already exists, M3d reads at most 8193 bytes and validates UTF-8, byte count, and digest:

- exact match becomes `already_applied` with `idempotent_noop=true`,
- any mismatch becomes `memory_store_target_conflict`.

The read-only check is not an atomic writer guarantee. A later writer must repeat the root, component, target, digest, and idempotency checks immediately before atomic replace/create.

## Runtime-private handoff

The runtime-private handoff may contain:

- candidate and namespace identifiers,
- target relative path,
- lineage fingerprint,
- idempotency key,
- page Markdown,
- page byte count and digest,
- target existence and idempotent no-op state.

It never contains raw message history, raw source text, or raw affect estimates. Explicit forbidden content-bearing source fields are rejected.

## Content-free projection

The public projection contains only:

- handoff/status/category counts,
- source event kind, memory kind, promotion policy, safety scope, and target category,
- page byte count,
- root/parent/target presence booleans,
- target digest match and idempotent no-op booleans,
- writer-apply-eligible count,
- bounded reason identifiers.

It omits:

- store root path,
- candidate ID and namespace,
- target path,
- lineage fingerprint and idempotency key,
- page Markdown and digest,
- raw source/message/affect content.

## Preserved non-goals

M3d does not:

- create, replace, rename, or delete files,
- create missing directories,
- update `memory/mem/index.md`,
- append to `memory/mem/log.md`,
- wire into request runtime,
- enqueue or execute a RelaySLP job,
- mutate RelaySOUL,
- expose a Lab API,
- change or delay visible response delivery,
- implement Secondary MEM consolidation.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_primary_writer_handoff.py \
  scripts/relaylm_relaymem_primary_writer_handoff_smoke.py \
  scripts/relaylm_relaymem_primary_writer_handoff_review_smoke.py \
  scripts/relaylm_relaymem_primary_writer_handoff_security_smoke.py

PYTHONPATH=. python scripts/relaylm_relaymem_primary_writer_handoff_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_writer_handoff_review_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_writer_handoff_security_smoke.py
```

Coverage includes default-off behavior, dry-run readiness, apply-preflight eligibility, idempotent existing-page detection, conflicting existing pages, malformed or tampered page metadata, non-canonical tokens, path traversal, Secondary-path substitution, symlink components, missing target directories, malformed UTF-8, strict booleans, forbidden raw-content fields, and content-free projection behavior.

## Next bounded slice

The next RelayMEM persistence slice should be separated from M3d:

```text
M3e atomic Primary MEM page writer
  -> consume only an exact M3d writer-eligible handoff
  -> repeat all path/root/digest/idempotency checks
  -> existing-root and existing-target-directory requirement
  -> bounded temp-file or exclusive-create strategy
  -> file fsync and atomic publication
  -> content-free result projection
  -> no index/log mutation in the same first writer slice
```

Index/log reconciliation should remain another explicit slice unless the atomicity and rollback contract is designed and tested together. Phase 6 queue/worker/dispatch idempotency remains separate from the RelayMEM memory-write idempotency key carried by M3d.
