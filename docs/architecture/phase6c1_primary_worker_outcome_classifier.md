---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_primary_worker_outcome_classifier
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - classifier input snapshots or transition intents change
  - worker or B3 outcome semantics change
  - RT-1 Primary writer authorization changes which failures may reach classification
  - RT-1D-R5 or R6 retires the Primary worker path
relaylm_not_authoritative_for:
  - queue transition execution
  - retry timing
  - protected source persistence
  - RT-1 cutover state or Primary writer authorization
  - Primary worker or pipeline admission
  - RT-1D-R5 or R6 retirement approval
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - ../contracts/slp/durable-queue.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../PROJECT_STATUS.md
---
# Phase 6-C1 Primary MEM Worker Outcome Classifier

Last reviewed: 2026-08-08 JST

## Status

Implementation handoff for the pure outcome-classification boundary. The classifier maps exact RelayMEM M3e/M3g/M3h outcome snapshots to Phase 6-B3 transition intent metadata without queue, filesystem, memory, clock, random, config, or RT-1 cutover I/O.

The authoritative worker contract remains `phase6c1_primary_mem_worker_contract.md`. This implementation does not own protected source construction, source consumption, queue transition execution, retry backoff, worker-loop composition, Primary writer admission, or cutover-state resolution.

Under RT-1D-R4, the classifier remains a retained Primary compatibility component only for work that has already passed the exact writer-decision gates at C2, C1-2, and C1-1. It is not an alternate path around those gates, and R5/R6 own final retirement/disposition of the Primary worker stack.

## Authorization boundary before classification

Writer authorization is resolved before this classifier is eligible to interpret a Primary memory outcome.

The live C1-2 worker sequence is:

```text
exact worker request validation
  -> exact Primary writer decision must permit write
       -> otherwise invalid_input / primary_writer_decision_rejected
       -> classifier not invoked for writer authorization
  -> B3 claim/source validation
  -> C1-1 pipeline execution under its own writer gate
  -> exact RelayMEM outcome snapshots
  -> this pure classifier
  -> bounded transition intent
```

`primary_writer_decision_rejected` is therefore an upstream authorization/input failure, not an M3 outcome classification. The classifier does not accept a writer decision, does not infer permission from queue/source/lease/store/idempotency state, and does not convert rejected authorization into retry, policy hold, terminal failure, recovery, or dry-run behavior.

A valid classifier result also does not grant writer permission. Classification describes what an already-admitted Primary execution observed; it cannot authorize a later worker invocation after the owning cutover path has fenced the writer.

## Public module

`relaylm/relaymem_slp_primary_worker_outcome.py`

The facade exports frozen exact snapshot types, a runtime-private outcome type, a strict content-free projection, and `classify_relaymem_slp_primary_worker_outcome`.

The public classifier interface remains free of RT-1 writer-decision inputs. Keeping authorization out of this pure function preserves its role as deterministic interpretation of exact RelayMEM evidence rather than a second cutover owner.

## Mapping

Durable success requires exact/idempotent M3e page publication, exact/idempotent M3g reconciliation, and M3h `recovery_not_required` with fully reconciled page/index/log evidence and no cleanup artifact. Missing M3h evidence cannot produce success.

M3g/M3h lock contention maps to `retry_release` with `transient_lock_contention`. Verified index-only progress maps to `primary_reconciliation_retry`. Policy-held/blocked, manual-confirmation, journaled-recovery, store conflict, and store corruption outcomes are terminal `commit_failed` intents. The classifier never produces `dead_letter`.

Unknown schemas/statuses, generic mappings, lookalike/subclass inputs, non-exact booleans, and incompatible stage combinations fail closed as `blocked_invalid_input`.

These mappings apply only after writer authorization has already admitted the worker/pipeline path. They describe durability, policy, consistency, and recovery outcomes; none is a writer-authorization state.

## Purity and ownership

The classifier owns only the pure mapping from exact protected RelayMEM snapshots to bounded Phase 6 transition intent metadata.

It does not:

- read or mutate B3 queue state,
- calculate retry timestamps,
- read protected source artifacts,
- inspect the RelayMEM filesystem,
- consume worker sources,
- perform M3 writes or recovery,
- resolve or refresh `SubjectiveMemRetrievalPrimaryWriterDecision`,
- interpret lease validity as writer permission,
- turn idempotent existing state into writer permission,
- execute a queue transition.

C1-2 owns the application of an accepted classification under its final exact B3 lease fence. RT-1 owns Primary writer authorization separately.

## Projection

The public projection exposes only schema/status, transition/terminal/retry/failure enums, terminal reason ID, and bounded booleans for retry, terminal, policy hold, manual confirmation, recovery isolation, and durable success.

It excludes memory content, paths, namespaces, runtime identities, lineage, idempotency keys, lease material, timestamps, exception text, private writer-decision identity, and nested source results.

## Validation

```bash
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_outcome_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_apply_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_recovery_audit_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_contract_smoke.py
```

The outcome smoke remains the direct authority for classifier purity and exact mapping behavior. Worker-level smokes separately prove that writer-decision rejection occurs before active-claim/source/pipeline execution and therefore before this classifier can be used for an admitted Primary execution outcome.

## RT-1D-R5 / R6 boundary

Current Project Status records R4 activation/P8 complete and R5 immediate retirement unstarted. This classifier therefore remains live only as part of the retained Primary compatibility worker stack.

R5/R6 own its final retirement or explicitly retained historical/test disposition after exact dependency characterization. This handoff does not authorize deleting the module, tests, or historical evidence ahead of that owning transaction.

Retirement must not be simulated by feeding writer authorization failures into the classifier, weakening exact outcome validation, or treating a classifier intent as permission to execute a Primary writer.
