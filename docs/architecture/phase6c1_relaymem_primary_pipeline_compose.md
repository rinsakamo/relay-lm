---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_relaymem_primary_pipeline_compose
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - RelayMEM Primary compose request, ledger, result, or projection schema changes
  - M3a-M3h result vocabulary or prerequisite semantics change
  - Phase 6-C1 one-claimed-job worker integration lands
relaylm_not_authoritative_for:
  - protected worker-source schema, persistence, retention, or deletion
  - B3 queue transitions, lease fencing, retry policy, or outcome classification
  - RelayMEM page, index, or log meaning owned by M3a-M3h
  - Secondary MEM, RelaySOUL mutation, or SOUL Lab runtime behavior
relaylm_related_authority:
  - phase6c1_primary_mem_worker_contract.md
  - relaymem_m3a_primary_formation_handoff.md
  - relaymem_m3d_primary_writer_handoff.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
---
# Phase 6-C1 RelayMEM Primary Pipeline Compose

## Status

Phase 6-C1-1 is implemented as a RelayMEM-owned production compose helper:

```python
execute_relaymem_primary_pipeline(request)
```

It consumes one exact request-local `RelayMEMSLPPrimaryWorkerSource`, validates and consumes that source through the C1-0 owner boundary, and fixes the canonical stage order:

```text
M3a formation
  -> M3b write preflight
  -> M3c page candidate
  -> M3d writer handoff
  -> M3e atomic page publication
  -> M3f reconciliation preflight
  -> M3g index-before-log apply
  -> M3h read-only recovery audit
```

The compose helper is not the Phase 6 worker. Queue claim, lease renewal and loss handling, retry release, terminal commit, backoff, stale recovery, source persistence, and scheduler behavior remain unimplemented here.

## Exact input boundary

The public request schema is:

```text
relaymem.primary_pipeline_request.v0
```

The request is an exact frozen runtime-private dataclass. It retains, with content-bearing fields excluded from `repr`:

- the exact C1-0 protected worker-source object,
- its exact request-local source scope,
- the exact claimed record used only by the C1-0 correlation validator,
- the configured store root,
- strict boolean `enabled`, `dry_run_only`, and `apply_enabled` gates.

Generic dictionaries, source lookalikes, wrong source schemas, cross-request scopes, consumed sources, source/claim correlation mismatch, bool/int confusion, contradictory gates, and incomplete apply gates fail before M3a.

The compose boundary does not validate an active lease or mutate the claimed record. C1-2 must perform lease fencing before source consumption and before M3e, M3g, and any B3 transition.

## Artifact handoff

Each existing M3 public helper remains directly available. Compose passes the exact returned private object to the next helper without reconstructing it:

- M3a `candidates` to M3b,
- complete M3b result plus one exact C1-0-derived source-lineage bridge to M3c,
- complete M3c result to M3d,
- complete M3d result to M3e,
- exact M3e receipt to M3f,
- exact M3f private plan to M3g,
- exact M3g receipt to M3h.

The lineage bridge uses the existing `relaymem.primary_source_lineage.v0` field set and preserves the protected source bundle's exact lineage fingerprint. It does not substitute the dispatch idempotency key or derive a new memory-write identity. M3b remains the sole owner of memory-write idempotency.

Every downstream M3 validator still executes. Compose additionally requires exact top-level result schemas and field sets before it records or forwards a stage result.

## Stop and audit rules

Policy block, policy hold, invalid prerequisites, schema drift, store conflict, and missing exact artifacts stop later stages. M3g lock contention returns immediately as a retryable compose observation; compose does not sleep, loop, or calculate backoff.

M3g results with an exact receipt proceed to M3h. M3h classifications remain RelayMEM results:

- `recovery_not_required`,
- `retry_reconciliation`,
- `manual_confirmation_required`,
- `journaled_recovery_candidate`.

Compose does not map these to `retry_release`, `commit_succeeded`, or `commit_failed`. The Phase 6 worker outcome classifier owns that mapping.

M3e post-publication uncertainty is never collapsed into success. The current M3f contract accepts only exact `applied` or `already_applied` M3e receipts, so an M3e uncertainty that cannot produce an M3g receipt stops with its exact M3e evidence. M3g partial or uncertain receipts continue to M3h when the existing M3h contract accepts them.

## Exact-existing page convergence

M3d already recognizes an exact existing page as `already_applied`. M3e validation now accepts two explicit, mutually exclusive exact M3d variants:

```text
ready:
  target absent
  writer_apply_eligible = true

already_applied:
  target exists
  target digest matches
  idempotent_noop = true
  writer_apply_eligible = false
```

Both variants retain the same strict field-set, content, path, digest, idempotency, and public-projection validation. This closes the full-chain retry gap: a new exact source invocation can rerun M3a-M3d, have M3e re-inspect the exact page, and continue through fresh M3f-M3h reconciliation without reconstructing a prior writer handoff.

## Dry-run and disabled behavior

Disabled mode executes no M3 stage and does not consume the source.

Dry-run mode consumes and validates the exact source, executes M3a-M3d, and reports `dry_run_ready`. It does not call M3e or M3g and does not claim durable success. M3f and M3h are not fabricated without durable receipts.

Apply mode requires:

```text
enabled = true
apply_enabled = true
dry_run_only = false
```

Existing helper gates remain authoritative and are passed without override.

## Runtime-private ledger and public projection

The result schema is:

```text
relaymem.primary_pipeline_result.v0
```

It stores one ordered entry for every exact stage enum, including explicit unexecuted entries. Private M3 results are excluded from dataclass `repr` and from log serialization.

The content-free projection schema is:

```text
relaymem.primary_pipeline_projection.v0
```

It exposes only bounded stage names, status, strict gate booleans, completed-stage count, block/hold/retry flags, page/reconciliation booleans, recovery classification, and bounded reason IDs. It explicitly reports that no queue I/O, B3 transition, lease operation, retry sleep, RelaySOUL mutation, or Secondary MEM processing occurred.

It omits governed messages, title and summary, page/index/log content, store paths, namespace, run/session/job/dispatch identifiers, lineage and hash values, memory-write keys, timestamps, exception text, and private M3 objects.

## Validation

```bash
python -m compileall -q \
  relaylm/relaymem_primary_pipeline.py \
  relaylm/_relaymem_primary_page_writer_handoff.py \
  relaylm/_relaymem_primary_page_writer_contract.py \
  scripts/relaylm_relaymem_primary_pipeline_smoke.py \
  scripts/relaylm_relaymem_primary_pipeline_security_smoke.py

PYTHONPATH=. python scripts/relaylm_relaymem_primary_pipeline_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_pipeline_security_smoke.py
```

The compose workflow also runs the existing M3a-M3h, C1-0 source, C1 worker-contract, and documentation-link smokes.

## Next boundary

The next I1 boundary is Phase 6-C1-2: one already-claimed job worker. It should combine:

```text
exact active B3 claim
  + exact protected worker source
  + lease checkpoints
  + execute_relaymem_primary_pipeline(...)
  + existing pure outcome classifier
  + lease-fenced B3 retry release or terminal commit
```

Protected source persistence remains a separate prerequisite for restart-complete execution. This compose helper neither persists nor reconstructs protected source content.
