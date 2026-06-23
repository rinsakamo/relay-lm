---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase6c1_integrated_worker_fault_smoke
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - one-claimed Primary MEM worker crash, lease, lock, retry, or terminal semantics change
  - Phase 6-C1 fault fixtures or integrated smoke coverage changes
  - durable protected worker-source persistence is implemented
relaylm_not_authoritative_for:
  - ordinary app.py or stream-final request-runtime source production
  - queue scanning, scheduling, daemon, worker-pool, or retry-timer ownership
  - RelayMEM M3a-M3h persistence semantics
  - protected source persistence, restart rehydration, retention, or cleanup
  - next-turn retrieval, RelayCTX injection, RelaySOUL mutation, or Secondary MEM
relaylm_related_authority:
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6b3_relayslp_queue_state_helpers.md
---
# Phase 6-C1-4 Integrated Worker Fault Smoke Handoff

## Status

Phase 6-C1-4 is complete as an integration-verification slice for the production one-claimed-job worker introduced by PR #367.

This slice does not add a second worker implementation, queue semantics, source schema, outcome mapping, persistence helper, scheduler, or runtime registry. It connects the canonical Thread C fault fixtures and existing production/test seams to the exact worker boundary:

```python
execute_relaymem_slp_primary_worker(request)
```

The verified production chain is:

```text
exact B3 claimed record
  + exact C1-0 protected source and request-local scope
  -> C1-2 lease-fenced one-claimed worker
  -> M3a-M3h compose
  -> pure worker outcome classifier
  -> canonical B3 retry_release or terminal transition
```

## Integrated safety evidence

The dedicated suite verifies the following behavior at the production worker boundary.

### Lease and crash fencing

- lease loss before source consumption leaves the source unconsumed and starts no M3 stage
- lease loss before M3e prevents page publication
- lease loss before M3g preserves an already-published page but prevents index/log reconciliation
- lease loss after M3h and before the B3 transition preserves durable memory state and rejects the stale terminal commit
- a successful renewal replaces the worker's expected durable record revision before later checkpoints and transition
- stale revision, owner, generation, token, and expired-lease requests cannot continue or transition the queue
- a generation N worker cannot act after generation N+1 becomes current
- two worker calls starting from one record revision produce exactly one current worker; the other is fenced before source consumption

### Crash convergence and idempotency

- an M3e-complete crash is recoverable by a new claim using a fresh canonical C1-0 source scope
- exact existing M3e state is recognized as `already_applied`
- the canonical index-before-log partial state is classified as `retry_reconciliation`
- the current claimant alone performs `retry_release`
- a later claim regenerates a fresh M3f plan and converges the pending log without duplicating page, index, or log entries
- a fully reconciled pre-terminal crash is recoverable without rollback and produces one terminal success transition
- dispatch identity and memory-write identity remain distinct

### Lock contention

The Thread C separate-process lock holder is used against production M3g and M3h paths.

- M3g exclusive-lock contention returns immediately as lock unavailable
- M3h audit contention remains read-only and is not reported as corruption
- neither path sleeps, spins, performs blind control-file replacement, or mutates index/log while contended
- the pure classifier maps both paths to `retry_release` with:
  - `retry_class = transient_lock_contention`
  - `failure_class = resource_contention`
- lease fields are cleared by the canonical B3 retry release
- after lock release, a new claim converges normally

### Outcome and terminal isolation

The worker-level outcome matrix verifies:

- durable M3e/M3g state plus `recovery_not_required` is the only success path
- policy held commits terminal failed with `memory_policy_held`
- policy blocked commits terminal failed with `memory_policy_blocked`
- manual confirmation commits terminal failed with `manual_confirmation_required`
- journaled recovery candidate commits terminal failed with `recovery_isolation_required`
- store corruption, conflict, divergence, page uncertainty, and control uncertainty are never classified as success
- source correlation failure commits terminal failed without memory mutation
- unsupported `held` or `dead_letter` queue states are not introduced
- stale claimants cannot perform retry or terminal transitions

### Source one-shot semantics

- one exact source can be consumed only once within its exact request-local scope
- a source remains available when lease fencing rejects the worker before source consumption
- cross-request and stale scopes remain invalid
- a retry or crash convergence run constructs a new exact C1-0 source and scope from the retained protected input boundary
- durable protected source persistence and restart rehydration are not claimed by this slice

### Content-free surfaces

Thread G-specific canaries cover message content, governed summary, namespace, dispatch identity, memory identity, lease token, queue path, and store path.

The suite verifies absence from:

- worker public projection
- `PipelineNodeResult`
- B3 public transition projection
- `repr` for worker request/result
- stdout and stderr
- serialized workflow-facing diagnostics

The CI runner captures all child-process stdout/stderr and emits only a bounded content-free script name and reason on failure. Its uploaded diagnostic never contains raw child output.

## Dedicated files

```text
scripts/relaylm_phase6c1_worker_fault_smoke.py
scripts/relaylm_phase6c1_worker_crash_convergence_smoke.py
scripts/relaylm_phase6c1_worker_lease_race_smoke.py
scripts/relaylm_phase6c1_worker_content_leakage_smoke.py
scripts/relaylm_phase6c1_worker_integration_ci_runner.py
.github/workflows/phase6c1-integrated-worker-fault-smoke.yml
```

The runner also re-executes the existing B3, C1-0 source, classifier, Thread C fixture/race, compose/security, C1-2 worker, M3e, M3g, M3h, Phase 6-C1 contract, and documentation-link smokes.

## Ownership and dependency boundaries

Thread C continues to own the reusable test-only fault fixture module. Thread F continues to own the production one-claimed worker and its functional/security smoke. Thread G owns only the integrated fault, convergence, race, leakage suite and this handoff.

The suite supplies an exact claimed record and exact protected source directly to the worker. It does not import or require the ordinary request-runtime producer or process-local registry associated with PR #365, and Issue #366 remains an ordinary request-runtime source-producer concern rather than a worker-safety dependency.

## Explicitly not implemented

This completion does not add:

- ordinary `app.py` or stream-finalizer worker wiring
- authoritative turn-index or governed-experience production
- queue scanner, scheduler, daemon, generalized worker pool, or retry scheduler
- worker-side sleep, jitter, or broad backoff engine
- durable protected source persistence
- restart-complete protected source rehydration
- next-turn memory retrieval or RelayCTX injection
- SOUL Lab APIs, memory correction, RelaySOUL mutation, Secondary MEM, TTS, audio, Live2D, or avatar execution

## Next Phase 6-C1 boundary

The next dependency boundary is Phase 6-C1-5:

> Durable protected source persistence

C1-5 must preserve the C1-0 protected-source and one-shot contracts while making exact source recovery restart-complete. C1-4 does not hide the current process-local or explicit-input limitation.
