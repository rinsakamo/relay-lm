---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_relaymem_primary_pipeline_compose
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - RelayMEM Primary compose request, ledger, result, or projection schema changes
  - M3a-M3h result vocabulary or prerequisite semantics change
  - Phase 6-C1 worker integration changes
  - RT-1 Primary writer decision carriage changes
  - RT-1D-R5 or R6 retires the Primary pipeline path
relaylm_not_authoritative_for:
  - protected worker-source schema, persistence, retention, or deletion
  - B3 queue transitions, lease fencing, retry policy, or outcome classification
  - RelayMEM page, index, or log meaning owned by M3a-M3h
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - Secondary MEM, RelaySOUL mutation, or SOUL Lab runtime behavior
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - relaymem_slp_current_target.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../evidence/implementation/relaymem-m3a-primary-formation-handoff.md
  - relaymem_m3d_primary_writer_handoff.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - ../PROJECT_STATUS.md
---
# Phase 6-C1 RelayMEM Primary Pipeline Compose

Last reviewed: 2026-08-08 JST

## Status

Phase 6-C1-1 remains implemented as the RelayMEM-owned production compose helper:

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

Under RT-1D-R4 the pipeline is a retained Primary compatibility writer surface, not independent writer authority. Its exact request carries the immutable RT-1 Primary writer decision, and the pipeline rejects a non-permitted decision before protected-source consumption or any M3 stage.

C1-2 invokes this helper under exact active B3 lease checkpoints and carries the same writer decision into it. C1-4 verifies crash, lease-loss, lock-contention, corruption, and retry convergence. C1-5 supplies restart rehydration of a fresh protected source for durably enqueued jobs. R5/R6 own final retirement/disposition of the Primary pipeline surface.

Compose remains queue-agnostic. It does not claim jobs, renew leases, calculate retry timing, perform B3 transitions, persist protected source, scan the queue, run a scheduler, or resolve RT-1 cutover state.

## Primary writer gate

`RelayMEMPrimaryPipelineRequest` carries one exact `SubjectiveMemRetrievalPrimaryWriterDecision`. The cutover domain owns whether that decision permits Primary mutation; compose only validates and consumes the caller-carried value.

The pipeline entry order is fail closed:

```text
exact pipeline-request validation
  -> exact carried Primary writer decision must permit write
       -> otherwise blocked / primary_writer_decision_rejected
       -> source remains unconsumed
       -> no M3a-M3h stage executes
  -> disabled / dry-run / apply behavior
  -> exact C1-0 source validation and consumption
  -> M3a-M3h according to existing gates and stop rules
```

The decision check occurs before protected-source consumption. A valid source, claimed record, store root, existing Primary page, previous retry, or successful historical pipeline run is therefore not writer authorization.

Compose does not re-resolve durable cutover state and cannot reconstruct a permitted decision from its other inputs. The worker validates the same carried decision before invoking compose, so the worker and pipeline are independent fail-closed boundaries over one immutable decision rather than two cutover-state owners.

`primary_writer_decision_rejected` is an authorization/input failure. It is not an M3 policy hold, reconciliation retry, recovery classification, dry-run fallback, or queue-transition instruction.

## Exact input boundary

The public request schema remains:

```text
relaymem.primary_pipeline_request.v0
```

The request is an exact frozen runtime-private dataclass containing:

- one exact `SubjectiveMemRetrievalPrimaryWriterDecision`,
- the exact C1-0 protected source object,
- its exact request-local source scope,
- the exact claimed record used by C1-0 correlation validation,
- the configured store root,
- strict boolean `enabled`, `dry_run_only`, and `apply_enabled` gates,
- exact runtime-private worker checkpoint callbacks where applicable.

Generic dictionaries, source lookalikes, wrong source schemas, cross-request scopes, consumed sources, source/claim mismatch, bool/int confusion, contradictory gates, incomplete apply gates, foreign writer decisions, and non-permitted writer decisions fail before M3a.

Compose does not own active lease validation. C1-2 fences execution before source consumption, M3e, M3g, and the final B3 transition. Those checkpoint callbacks protect B3 claim/lease ownership; they do not refresh or replace the RT-1 writer decision.

## Exact artifact handoff

Every existing M3 public helper remains directly available. Compose passes exact private artifacts without reconstructing them:

- M3a candidates to M3b,
- exact M3b result and C1-0-derived lineage bridge to M3c,
- exact M3c result to M3d,
- exact M3d result to M3e,
- exact M3e receipt to M3f,
- exact M3f private plan to M3g,
- exact M3g receipt to M3h.

The lineage bridge preserves the protected source lineage fingerprint. It does not substitute the dispatch idempotency key or derive memory-write identity. M3b remains the sole owner of memory-write idempotency.

Every downstream validator still executes. Compose also requires exact top-level schemas and field sets before forwarding stage results. None of those artifact identities grants RT-1 writer permission.

## Stop and audit rules

Policy block, policy hold, invalid prerequisites, schema drift, store conflict, missing exact artifacts, and impossible stage combinations stop later stages.

M3g lock contention returns immediately as a retryable compose observation. Compose does not sleep, loop, or calculate backoff.

M3g results with an exact receipt proceed to M3h. M3h classifications remain RelayMEM results:

- `recovery_not_required`,
- `retry_reconciliation`,
- `manual_confirmation_required`,
- `journaled_recovery_candidate`.

Compose does not map these to queue transitions. C1-3 owns the pure mapping and C1-2 owns the actual B3 transition under the final lease fence.

M3e/M3g durability uncertainty is never collapsed into success. A rejected RT-1 writer decision is earlier than all of these M3 outcomes and cannot be converted into one of them.

## Exact-existing page convergence

M3d and M3e recognize two exact variants:

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

Both variants preserve strict path, content, digest, idempotency, and projection validation. A new claim may rerun M3a-M3d, recognize an exact existing page, regenerate M3f from current state, and converge M3g/M3h without reconstructing a prior in-memory plan, but that later pipeline invocation still requires its caller-carried exact permitted writer decision.

Idempotent existing-page convergence is a memory-write consistency property, not an authorization bypass.

## Gates

The RT-1 writer-decision gate is evaluated before the existing mode gates. A pipeline request with a non-permitted decision fails closed even if it would otherwise be disabled or dry-run.

With an exact permitted writer decision:

- disabled mode executes no M3 stage and does not consume the source;
- dry-run validates and consumes the exact source, executes M3a-M3d, and reports `dry_run_ready`; it does not call M3e or M3g and does not claim durable success;
- apply mode requires:

```text
enabled = true
apply_enabled = true
dry_run_only = false
```

Existing helper gates remain authoritative after the writer gate. No mode converts `rejected` into permission.

## Runtime-private ledger and public projection

The result schema remains:

```text
relaymem.primary_pipeline_result.v0
```

It records an ordered entry for every exact stage, including explicit unexecuted entries. Private M3 results are excluded from dataclass `repr` and log serialization.

The content-free projection schema remains:

```text
relaymem.primary_pipeline_projection.v0
```

It exposes bounded stage names, statuses, booleans, counts, recovery classification, and reason IDs. It reports that compose itself performs no queue scanning, B3 transition, retry sleep, RelaySOUL mutation, or Secondary MEM processing.

It omits governed messages, title/summary, page/index/log content, store paths, namespace, runtime identifiers, lineage, hashes, memory-write keys, timestamps, exception text, private writer-decision identity, and private M3 objects.

## Validation

```bash
PYTHONPATH=. python scripts/relaylm_relaymem_primary_pipeline_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_pipeline_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_worker_integration_ci_runner.py
```

The repository workflow/test registry remains command authority; this list records the compose regression boundary.

## Current integration boundary

The one-job adapter and one-claimed worker are now implemented above compose:

```text
one exact queued record
  + exact Primary writer decision
  -> C2 pre-claim writer gate
  -> B3 claim
  -> C1-5 rehydrate
  -> fresh C1-0 source/scope
  -> C1-2 worker writer gate
  -> this compose helper writer gate
  -> M3a-M3h
```

Compose remains queue-agnostic and neither persists nor reconstructs protected source content. The repeated writer checks are defense in depth over the same carried authorization, not separate authority decisions.

## RT-1D-R5 / R6 boundary

Current Project Status records R4 activation/P8 complete and R5 immediate retirement unstarted. The compose helper therefore remains a live retained Primary compatibility surface, but it can execute only after its exact writer-decision gate.

R5/R6 own final retirement or explicitly retained read-only disposition of Primary writer/pipeline surfaces after exact dependency characterization. This handoff does not authorize deleting runtime code, durable evidence, or pipeline tests ahead of the owning retirement transaction.

Retirement must not be simulated by weakening source validation, bypassing the writer decision, treating rejected authorization as dry-run/recovery permission, or moving Primary mutation semantics into another owner.
