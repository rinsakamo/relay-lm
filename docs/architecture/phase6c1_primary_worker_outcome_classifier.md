---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_primary_worker_outcome_classifier
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - classifier input snapshots or transition intents change
  - worker or B3 outcome semantics change
relaylm_not_authoritative_for:
  - queue transition execution
  - retry timing
  - protected source persistence
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6b3_relayslp_queue_state_helpers.md
---
# Phase 6-C1 Primary MEM Worker Outcome Classifier

Implementation handoff for the pure outcome-classification boundary. The classifier maps exact RelayMEM M3e/M3g/M3h outcome snapshots to Phase 6-B3 transition intent metadata without queue, filesystem, memory, clock, random, or config I/O.

The authoritative contract remains `phase6c1_primary_mem_worker_contract.md`. This implementation does not own protected source construction, source consumption, queue transition execution, retry backoff, or worker-loop composition.

## Public module

`relaylm/relaymem_slp_primary_worker_outcome.py`

The facade exports frozen exact snapshot types, a runtime-private outcome type, a strict content-free projection, and `classify_relaymem_slp_primary_worker_outcome`.

## Mapping

Durable success requires exact/idempotent M3e page publication, exact/idempotent M3g reconciliation, and M3h `recovery_not_required` with fully reconciled page/index/log evidence and no cleanup artifact. Missing M3h evidence cannot produce success.

M3g/M3h lock contention maps to `retry_release` with `transient_lock_contention`. Verified index-only progress maps to `primary_reconciliation_retry`. Policy-held/blocked, manual-confirmation, journaled-recovery, store conflict, and store corruption outcomes are terminal `commit_failed` intents. The classifier never produces `dead_letter`.

Unknown schemas/statuses, generic mappings, lookalike/subclass inputs, non-exact booleans, and incompatible stage combinations fail closed as `blocked_invalid_input`.

## Projection

The public projection exposes only schema/status, transition/terminal/retry/failure enums, terminal reason ID, and bounded booleans for retry, terminal, policy hold, manual confirmation, recovery isolation, and durable success.

It excludes memory content, paths, namespaces, runtime identities, lineage, idempotency keys, lease material, timestamps, exception text, and nested source results.

## Validation

```bash
PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_outcome_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_apply_smoke.py
PYTHONPATH=. python scripts/relaylm_relaymem_primary_index_log_recovery_audit_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_contract_smoke.py
```
