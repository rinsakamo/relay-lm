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
relaylm_not_authoritative_for:
  - ordinary app.py or stream-final request-runtime source production
  - queue scanning, scheduling, daemon, worker-pool, or retry-timer ownership
  - RelayMEM M3a-M3h persistence semantics
  - protected source artifact schema or retention implementation
  - next-turn retrieval, RelayCTX injection, RelaySOUL mutation, or Secondary MEM
relaylm_related_authority:
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6b3_relayslp_queue_state_helpers.md
---
# Phase 6-C1-4 Integrated Worker Fault Smoke Handoff

## Status

Phase 6-C1-4 is complete as integration verification for the production one-claimed worker.

It does not add another worker implementation, queue semantic, source schema, persistence helper, scheduler, or runtime registry. It connects the canonical Thread C fixtures and production/test seams to:

```python
execute_relaymem_slp_primary_worker(request)
```

Verified chain:

```text
exact B3 claimed record
  + exact C1-0 protected source and one-shot scope
  -> C1-2 lease-fenced worker
  -> C1-1 M3a-M3h compose
  -> C1-3 outcome classifier
  -> canonical B3 retry_release or terminal transition
```

## Integrated safety evidence

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

### Crash convergence and idempotency

The suite verifies:

- M3e-complete crash converges under a new claim,
- exact existing page is recognized as `already_applied`,
- index-applied/log-pending is classified as reconciliation retry,
- only the current claimant performs retry release,
- a later claim regenerates M3f and converges the pending log,
- fully reconciled pre-terminal crash converges to one terminal success,
- dispatch identity and memory-write identity remain distinct.

### Lock contention

Separate-process lock holders exercise production M3g and M3h paths.

- M3g exclusive-lock contention returns immediately,
- M3h audit contention remains read-only,
- neither path sleeps, spins, blindly replaces control files, or mutates while contended,
- C1-3 maps valid contention to bounded `retry_release`,
- canonical B3 retry release clears lease fields,
- a new claim converges after lock release.

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

### Source one-shot semantics

The suite verifies:

- one exact C1-0 source is consumed once within its scope,
- lease rejection before consumption leaves it unconsumed,
- cross-request and stale scopes are invalid,
- a retry/new claim receives a fresh source and scope from retained claim-independent evidence.

C1-4 originally used explicit live-process input. C1-5 now supplies the same claim-independent evidence through a durable protected artifact after restart without weakening one-shot semantics.

### Content-free surfaces

Leakage canaries cover message content, governed summary, namespace, dispatch identity, memory identity, lease token, queue path, store path, and source-artifact material.

The suite verifies absence from:

- worker public projection,
- `PipelineNodeResult`,
- B3 public transition projection,
- request/result `repr`,
- stdout and stderr,
- workflow-facing diagnostics.

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

The runner also executes B3, C1-0, classifier, compose, C1-2, M3e, M3g, M3h, contract, and documentation regressions.

## Ownership and dependency boundaries

Thread C owns reusable test-only fault fixtures. Thread F owns production C1-2 and functional/security smoke. Thread G/C1-4 owns the integrated fault, convergence, race, corruption, and leakage suite.

The suite accepts exact claimed input and exact source at the worker boundary. It does not own ordinary request production, queue scanning, scheduler lifecycle, or next-turn recall.

## Explicitly not implemented by C1-4

C1-4 does not add:

- ordinary app/stream-finalizer worker invocation,
- queue scanner, scheduler, daemon, worker pool, or retry timer service,
- the one-job queued-record claim/rehydrate adapter,
- next-turn retrieval or RelayCTX injection,
- SOUL Lab APIs or memory correction,
- RelaySOUL mutation, Secondary MEM, TTS, audio, Live2D, or avatar execution.

## Subsequent boundary

C1-5 now preserves C1-0 source correlation and one-shot contracts while making protected-source recovery restart-complete for durably enqueued jobs.

The next integration boundary is a thin one-job queued-record adapter using canonical B3 claim, C1-5 rehydration, and C1-2 execution. Next-turn retrieval and RelayCTX injection follow after that adapter.
