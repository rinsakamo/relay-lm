---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_integrated_worker_fault_smoke
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - one-claimed worker crash, lease, lock, retry, or terminal semantics change
  - Phase 6-C1 fault fixtures or integrated smoke coverage changes
  - durable protected worker-source persistence changes
  - RT-1 Primary writer-decision admission changes the reachable worker fault surface
  - RT-1D-R5 or R6 retires the Primary worker path
relaylm_not_authoritative_for:
  - ordinary app.py or stream-final request-runtime source production
  - queue scanning, scheduling, daemon, worker-pool, or retry-timer ownership
  - RelayMEM M3a-M3h persistence semantics
  - protected source artifact schema or retention implementation
  - RT-1 cutover state, Primary writer authorization, or retirement approval
  - next-turn retrieval, RelayCTX injection, RelaySOUL mutation, or Secondary MEM
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - ../contracts/slp/durable-queue.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../PROJECT_STATUS.md
---
# Phase 6-C1-4 Integrated Worker Fault Smoke Handoff

Last reviewed: 2026-08-08 JST

## Status

Phase 6-C1-4 is complete as integration verification for the production one-claimed worker. Under current RT-1D-R4 semantics, that worker is a retained Primary compatibility writer surface whose execution is admitted only by the exact Primary writer decision owned outside C1-4.

C1-4 does not add another worker implementation, queue semantic, source schema, persistence helper, scheduler, runtime registry, or writer-authority mechanism. It connects the canonical Thread C fixtures and production/test seams to:

```python
execute_relaymem_slp_primary_worker(request)
```

The fault suite verifies behavior after the worker path has been validly admitted. Writer-decision rejection is a separate upstream authorization/input boundary owned by C2/C1-2/C1-1 and must not be relabeled as a lease, crash, retry, policy, or corruption outcome.

Current verified chain:

```text
exact RT-1 Primary writer decision
  -> non-permitted: fail closed before C1-4 worker fault surface is entered
  -> permitted:
       exact B3 claimed record
       + exact C1-0 protected source and one-shot scope
       -> C1-2 lease-fenced worker
       -> C1-1 M3a-M3h compose
       -> C1-3 outcome classifier
       -> canonical B3 retry_release or terminal transition
```

C1-4 therefore records fault/convergence evidence for an admitted Primary worker; it is not evidence that Primary writer authority remains available after `primary_writer_fenced`.

## Integrated safety evidence

### Writer-fence relationship

The current worker regression umbrella verifies the writer-decision gate separately from C1-4's dedicated fault scenarios:

- a foreign/non-permitted decision is rejected before active-claim validation, source consumption, pipeline execution, or outcome classification,
- C1-1 independently checks the same caller-carried immutable decision before protected-source consumption/M3 execution,
- B3 lease checkpoints do not re-resolve or refresh RT-1 cutover state,
- retained queue/source/idempotency evidence does not grant permission for a later Primary writer invocation.

The C1-4 dedicated crash/lease/lock fixtures remain scoped to behavior after valid admission. This separation prevents a fault test from becoming a second writer-authority definition.

### Lease and crash fencing

The suite verifies:

- lease loss before source consumption starts no M3 stage,
- lease loss before M3e prevents page publication,
- lease loss before M3g preserves page state but prevents control-file mutation,
- lease loss after M3h prevents stale terminal commit,
- renewal replaces expected durable record revision,
- stale revision, owner, generation, token, and expired leases cannot continue,
- generation N cannot act after generation N+1 becomes current,
- competing calls from one revision yield one current worker and one fenced rejection.

These are B3 claim/lease fences after writer admission. They are not replacements for the RT-1 writer-decision gate.

### Crash convergence and idempotency

The suite verifies:

- M3e-complete crash converges under a new claim,
- exact existing page is recognized as `already_applied`,
- index-applied/log-pending is classified as reconciliation retry,
- only the current claimant performs retry release,
- a later claim regenerates M3f and converges the pending log,
- fully reconciled pre-terminal crash converges to one terminal success,
- dispatch identity and memory-write identity remain distinct.

A later claim or idempotent existing-page state still requires exact writer permission for that invocation. Crash convergence and idempotency preserve consistency, not authorization.

### Lock contention

Separate-process lock holders exercise production M3g and M3h paths.

- M3g exclusive-lock contention returns immediately,
- M3h audit contention remains read-only,
- neither path sleeps, spins, blindly replaces control files, or mutates while contended,
- C1-3 maps valid contention to bounded `retry_release`,
- canonical B3 retry release clears lease fields,
- a new claim converges after lock release.

Lock availability and retryability are operational conditions only; neither can convert a rejected writer decision into permission.

### Outcome and terminal isolation

The worker matrix verifies:

- exact durable M3e/M3g state plus M3h `recovery_not_required` is the only success path,
- policy held/blocked becomes terminal failed without false queue corruption,
- manual confirmation and recovery isolation never auto-apply,
- page/control corruption and unsafe file types never produce success,
- state divergence and unverified state remain terminal-safe,
- durability uncertainty cannot produce success,
- source correlation failure mutates no memory,
- unsupported `held` or `dead_letter` states are not introduced,
- stale claimants cannot transition queue state.

These classifications are reachable only after writer admission. `primary_writer_decision_rejected` remains an upstream authorization/input failure and is not one of these fault or terminal meanings.

### Source one-shot semantics

The suite verifies:

- one exact C1-0 source is consumed once within its scope,
- lease rejection before consumption leaves it unconsumed,
- cross-request and stale scopes are invalid,
- a retry/new claim receives a fresh source and scope from retained claim-independent evidence.

C1-4 originally used explicit live-process input. C1-5 now supplies the same claim-independent evidence through a durable protected artifact after restart without weakening one-shot semantics.

Source durability preserves evidence and retryability only. A rehydrated source does not preserve writer permission across a later invocation.

### Content-free surfaces

Leakage canaries cover message content, governed summary, namespace, dispatch identity, memory identity, lease token, queue path, store path, and source-artifact material.

The suite verifies absence from:

- worker public projection,
- `PipelineNodeResult`,
- B3 public transition projection,
- request/result `repr`,
- stdout and stderr,
- workflow-facing diagnostics.

Writer-decision identity remains runtime-private under the current worker contract and is not added to C1-4 public diagnostics.

## Dedicated files

```text
scripts/relaylm_phase6c1_worker_fault_smoke.py
scripts/relaylm_phase6c1_worker_crash_convergence_smoke.py
scripts/relaylm_phase6c1_worker_lease_race_smoke.py
scripts/relaylm_phase6c1_worker_corruption_smoke.py
scripts/relaylm_phase6c1_worker_content_leakage_smoke.py
scripts/relaylm_phase6c1_worker_integration_ci_runner.py
.github/workflows/phase6c1-integrated-worker-fault-smoke.yml
```

The runner also executes B3, C1-0, classifier, compose, C1-2, M3e, M3g, M3h, contract, and documentation regressions. Those broader regressions are where the current writer-decision admission boundary is verified; the dedicated C1-4 fault cases keep their original crash/lease/lock/corruption responsibility.

## Ownership and dependency boundaries

Thread C owns reusable test-only fault fixtures. Thread F owns production C1-2 and functional/security smoke. Thread G/C1-4 owns the integrated fault, convergence, race, corruption, and leakage suite.

The suite accepts exact claimed input and exact source at the worker boundary after writer admission. It does not own ordinary request production, queue scanning, scheduler lifecycle, next-turn recall, RT-1 cutover-state resolution, or writer permission.

## Explicitly not implemented by C1-4

C1-4 does not add:

- ordinary app/stream-finalizer worker invocation,
- queue scanner, scheduler, daemon, worker pool, or retry timer service,
- the one-job queued-record claim/rehydrate adapter,
- next-turn retrieval or RelayCTX injection,
- SOUL Lab APIs or memory correction,
- RelaySOUL mutation, Secondary MEM, TTS, audio, Live2D, or avatar execution,
- RT-1 writer-decision resolution or retirement control.

These are C1-4 scope exclusions, not repository-wide status claims. In particular, the one-job adapter and next-turn retrieval/scope-isolation items were later completed by C2 and Phase I-1; the status of the other excluded capabilities is owned by Project Status and their relevant current authorities.

## Current downstream boundary

C1-5 preserves C1-0 source correlation and one-shot contracts while making protected-source recovery restart-complete for durably enqueued jobs. C2 now owns the thin one-job queued-record claim/rehydrate adapter, and Phase I-1 completed the historically subsequent next-turn recall/scope-isolation integration.

Under current RT-1 semantics those completed capabilities remain compatibility/history evidence only where they concern the replaced Primary path. They do not preserve ordinary Primary reader or writer authority after the owning cutover decisions fence those classes.

R5/R6 own final retirement or explicitly retained historical/test disposition of the Primary worker/fault surfaces after exact dependency characterization. C1-4 does not authorize deletion, validator weakening, or movement of Primary mutation semantics to another owner.
