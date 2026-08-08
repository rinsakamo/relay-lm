---
relaylm_doc_type: implementation_handoff
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - Primary MEM writer handoff schema changes
  - M3e-M3h page/index/log persistence ownership changes
  - RT-1 Primary writer-decision carriage changes which production calls may reach M3d
  - RT-1D-R5 or R6 retires the Primary writer path
relaylm_not_authoritative_for:
  - Phase 6 queue worker retry orchestration
  - request-runtime RelaySLP admission or enqueue wiring
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - Secondary MEM consolidation semantics
  - repository-wide implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6c1_relaymem_primary_pipeline_compose.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_mvp_design.md
  - memory_lifecycle_design.md
  - pipeline_implementation_plan.md
  - relaymem_slp_current_target.md
  - ../PROJECT_STATUS.md
---
# RelayMEM-M3d Primary Writer Handoff Preflight

Last reviewed: 2026-08-08 JST

## Status

RelayMEM-M3d remains implemented as a helper-only, read-only Primary MEM writer-handoff preflight.

It consumes the exact RelayMEM-M3c Primary MEM page-candidate artifact, revalidates the candidate and configured store target, and emits one bounded runtime-private writer handoff plus a content-free projection.

M3d does not perform a filesystem write. In the current production compose path, M3e owns atomic page publication, M3f owns reconciliation preflight, M3g owns index-before-log reconciliation apply, and M3h owns read-only recovery audit.

Under RT-1D-R4, M3d is a retained Primary compatibility component below the exact Primary writer-decision gate. The production C1-1 pipeline rejects a non-permitted writer decision before protected-source consumption and before any M3a-M3h stage, so a normal production invocation can reach M3d only after writer admission has already succeeded.

M3d itself does not accept, resolve, cache, refresh, or reconstruct the RT-1 writer decision. Its `ready`, `already_applied`, writer-handoff, path, digest, idempotency, or store-state results describe preflight consistency only; none grants Primary mutation authority.

R5/R6 own final retirement or explicitly retained read-only/test disposition of this Primary compatibility surface after exact dependency characterization.

## Read-only responsibility inside the current pipeline

M3d was originally introduced before the durable page/index/log apply slices existed. That historical sequencing is complete. The current retained compatibility chain is:

```text
exact RT-1 Primary writer decision
  -> rejected: C1-1 stops before any M3 stage
  -> permitted:
       M3a formation
       -> M3b write preflight
       -> M3c page candidate
       -> M3d writer-handoff preflight      read-only
       -> M3e atomic page publication       mutation
       -> M3f reconciliation preflight      read-only
       -> M3g index-before-log apply        mutation
       -> M3h recovery audit                read-only
```

M3d remains intentionally read-only even though its downstream owners now exist. It establishes the exact RelayMEM-owned page handoff and repeats target-state checks without duplicating M3e publication or M3f-M3h reconciliation semantics.

Direct helper tests may exercise M3d independently to prove its contract. Such direct invocation is contract/regression evidence, not a second production writer-admission path and not evidence that a Primary writer remains permitted after `primary_writer_fenced`.

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

These helper gates govern M3d preflight behavior only. They are not RT-1 writer authorization and cannot convert a rejected writer decision into permission.

## Exact M3c revalidation

M3d revalidates:

- exact M3c result and page-candidate schemas,
- helper/read-only/no-side-effect flags,
- candidate cardinality and status,
- strict boolean fields,
- Primary memory layer, memory kind, target category, promotion policy, and safety scope,
- namespace, lineage fingerprint, and deterministic M3b idempotency-key recomputation,
- deterministic Primary MEM target path,
- UTF-8 page encoding and bounded page size,
- page byte count and SHA-256 digest,
- deterministic front-matter field set and order,
- page metadata correspondence with the candidate,
- deterministic page body and summary character count,
- upstream M3c writer-handoff eligibility when M3d apply preflight is requested.

Arbitrary upstream blocked reasons are not copied into the M3d public projection. They collapse to bounded M3d reason identifiers.

Exact M3c/M3d validity is a prerequisite for downstream persistence after admission. It does not independently authorize persistence.

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

The read-only check is not an atomic writer guarantee. M3e repeats the root, component, target, digest, and idempotency checks immediately before atomic page publication.

`ready` and `already_applied` remain storage/preflight states. Neither says that the current RT-1 writer decision permits a Primary mutation. In particular, an exact existing Primary page, matching digest, usable store root, or prior successful write cannot revive writer authority after the upstream cutover owner has fenced that writer class.

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

The handoff intentionally contains no RT-1 writer-decision identity. It is a page-preflight artifact forwarded by an already-admitted compose invocation, not a durable authorization token that can be replayed later.

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
- raw source/message/affect content,
- private RT-1 writer-decision identity.

A content-free projection is observability only and cannot be used to reconstruct or infer writer permission.

## Preserved non-goals

M3d does not:

- create, replace, rename, or delete files,
- create missing directories,
- update `memory/mem/index.md`,
- append to `memory/mem/log.md`,
- wire into request runtime,
- enqueue or execute a RelaySLP job,
- resolve or refresh RT-1 cutover state,
- grant or persist Primary writer authorization,
- mutate RelaySOUL,
- expose a Lab API,
- change or delay visible response delivery,
- implement Secondary MEM consolidation.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_primary_writer_handoff.py \
  relaylm/_relaymem_primary_writer_handoff_impl.py \
  scripts/relaylm_relaymem_primary_writer_handoff_smoke.py \
  scripts/relaylm_relaymem_primary_writer_handoff_review_smoke.py \
  scripts/relaylm_relaymem_primary_writer_handoff_security_smoke.py \
  scripts/relaylm_relaymem_primary_writer_handoff_idempotency_smoke.py

PYTHONPATH=. python scripts/relaylm_relaymem_primary_writer_handoff_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_writer_handoff_review_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_writer_handoff_security_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_writer_handoff_idempotency_smoke.py
```

Coverage includes default-off behavior, dry-run readiness, apply-preflight eligibility, deterministic M3b idempotency-key recomputation, idempotent existing-page detection, conflicting existing pages, malformed or tampered page metadata, non-canonical tokens, path traversal, Secondary-path substitution, symlink components, missing target directories, malformed UTF-8, strict booleans, forbidden raw-content fields, and content-free projection behavior.

The current Phase 6-C1 pipeline/worker regression umbrella separately proves that a non-permitted Primary writer decision stops before M3d is reached. M3d's dedicated smokes remain contract/security/idempotency tests rather than writer-authorization tests.

## Current downstream boundary

M3d is no longer waiting for later persistence slices. Its exact handoff feeds the implemented M3e-M3h owners inside C1-1:

```text
M3d exact writer-eligible handoff
  -> M3e atomic Primary MEM page writer
  -> M3f Primary MEM index/log reconciliation preflight
  -> M3g Primary MEM index/log reconciliation apply
  -> M3h Primary MEM reconciliation recovery audit
```

M3d retains memory-write identity/path/content preflight ownership; M3e owns page publication; M3f owns the deterministic reconciliation plan; M3g owns index-before-log mutation; M3h owns read-only recovery classification. Phase 6 queue/dispatch/worker idempotency remains separate from the RelayMEM memory-write idempotency key carried by M3d.

All of these Primary persistence capabilities remain subordinate to the exact upstream RT-1 writer decision in production. R5/R6 own their final retirement or explicitly retained historical/read-only/test disposition. This handoff does not pre-authorize deletion, weaken the preflight contract, or move Primary mutation semantics to another owner.
