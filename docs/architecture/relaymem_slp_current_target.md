---
relaylm_doc_type: current_target_migration
relaylm_authority: relaymem_relayslp_current_target
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - RelayMEM or RelaySLP producer consumer boundary changes
  - Phase 6 deferred orchestration slice lands
  - durable MEM persistence apply state changes
  - ordinary-runtime worker integration changes
  - I1-G or O1 boundary changes
relaylm_not_authoritative_for:
  - repository-wide phase sequencing
  - exact RelayMEM or RelaySLP schemas
  - RelaySOUL approval contracts
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - i1gd_durable_finalization_retention_cleanup.md
  - i1ge_durable_finalization_crash_validation.md
  - o0_local_one_job_runner.md
  - o1a_two_lane_scheduler_contract.md
  - o1b_sealed_i1g_replay_lane.md
  - o1c_eligible_b2_queue_lane.md
  - o1d1_production_scheduler_round.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - phase_i4c2_primary_forget_recovery_finalization.md
  - phase_i4d_primary_retrieval_exclusion.md
  - relaymem_mvp_implementation_plan.md
  - pipeline_implementation_plan.md
  - wave3_cross_slice_convergence_audit.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

Last reviewed: 2026-06-27 JST

## Current implemented boundary

RelayMEM currently provides bounded store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, gated RelayCTX injection, auditable Correct, canonical read-only Primary current-state resolution, I-4C1 hidden-successor lifecycle commit ownership, bounded I-4C2 recovery/finalization, and I-4D ordinary retrieval lifecycle exclusion plus historical lifecycle overlay.

The Primary MEM persistence chain is implemented through M3a-M3h. The Phase 6 execution boundary is implemented through B0-B3, C1-5, and C2, with O0 as the explicit local caller:

```text
B0 durable queue contract
B1 dispatch preflight
B2 atomic durable enqueue
B3 queue claim/lease/retry/terminal lifecycle
C1-0 exact current-claim protected source
C1-1 canonical M3a-M3h compose
C1-2 lease-fenced one-already-claimed worker
C1-3 pure outcome classification
C1-4 integrated fault/crash convergence
C1-5 durable claim-independent protected source and restart rehydration
C2 one-job claim/rehydrate/execute adapter
O0 one invocation -> at most one eligible queued job
```

Phase 6-B2 performs atomic durable enqueue of durably enqueued jobs through the existing content-free queue record authority. Phase 6-B3 performs default-off, dry-run-first fenced queue lifecycle transitions. C1-2 executes one already-claimed canonical B3 job. C1-5 persists protected content separately from the content-free queue. C2 accepts one caller-selected queued record and connects B3 claim, C1-5 preparation, and C1-2 execution. O0 adds bounded discovery and one C2 delegation without polling or retry scheduling.

## I1-G durable-finalization boundary

I1-GA through I1-GE are complete:

```text
I1-GA contract / fault model
  -> I1-GB sealed evidence before protected visible release
  -> I1-GC caller-selected one-record replay
       -> exact finalized-turn reconstruction
       -> existing A1/A2/B1
       -> exact C1-5 source
       -> exact B2 queue
       -> canonical downstream reread
       -> immutable completion marker
  -> I1-GD one bounded maintenance pass
       -> complete bounded inventory
       -> shared per-record fence and existing root mutation lock
       -> retain sealed pending | isolate | clean known components | block
       -> isolation marker removed last
  -> I1-GE real process-exit/fresh-restart validation
```

I1-G completion means sealed evidence, exact C1-5 source, exact B2 queue correlation, durable completion, retention/isolation lifecycle, and crash-at-every-boundary validation. It does not imply B3 terminal success, C2 execution, worker execution, Primary MEM formation, semantic quality, retrieval use, automatic scheduling, polling, supervision, or always-on operation.

## O1 scheduler boundary

O1A defines a pure scheduler contract. O1B and O1C bounded production discovery and delegation are complete. O1D1 accepts the five exact scheduler gates, invokes O1B then O1C at most once each, aggregates through O1A, validates the content-free projection, and returns without sleeping:

```text
one bounded round
  -> replay lane first
       -> O1B discovery
       -> one existing I1-GC delegation
  -> queue lane second
       -> O1C discovery
       -> one existing C2 delegation
  -> stop | run_next_round | idle
  -> return without sleep
```

Replay and queue remain independent state machines. A B2 record converged by replay may be selected in the same round only through independent queue-root discovery and canonical reread. Replay output is never a C2 input. O1D2 fairness/retry-time/backoff/jitter/pacing, O1E stale recovery/shutdown, O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented.

The accepted O1D1 scheduler fields are in `relaylm/config.py`, `docs/config_schema.md`, and `config.example.yaml`:

```yaml
relaymem_local_scheduler_enabled: false
relaymem_local_scheduler_dry_run_only: true
relaymem_local_scheduler_apply_enabled: false
relaymem_local_scheduler_replay_lane_enabled: true
relaymem_local_scheduler_queue_lane_enabled: true
```

## Current Primary mutation and lifecycle-read boundary

Phase I-3 Correct provides exact character/namespace/logical-memory/physical-page/revision validation, read-only preflight, bounded semantic diff, short-lived token, shared per-memory lock and pending-operation fence, immutable successor page, M3f/M3g convergence, prepared/applied recovery, exact replay, immutable correction receipt, M2 current-revision resolution, and historical used-memory integrity.

Phase I-4B provides:

```text
relaylm.mem.primary_current_state.v0
lifecycle_state: active | hidden
mutation_state: none | prepared | recovery_required | corrupt
retrieval_eligible: true | false
```

I-4C1 revalidates the exact token/reason under the shared lock, publishes immutable prepared evidence, constructs the deterministic hidden successor, delegates publication to M3e, and returns `hidden / recovery_required / false` until finalization.

I-4C2 resumes one exact durable prepare, reuses the shared mutation fence and deterministic I-4C1 successor, performs operation-scoped index-before-log convergence through existing M3f/M3g authorities, canonically verifies page/control correlation, publishes `relaylm.mem.forget_tombstone.v0`, and supports exact replay. The public governance resolver reaches `hidden / none / false`.

I-4D consumes the complete shared current-state authority before snippet construction. It excludes hidden, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, unresolved, and prior physical revisions from ordinary M2/RelayCTX and backend-bound request construction. It does not rewrite historical used-memory receipts and adds the separate read-only `relaylm.lab.memory_used_lifecycle.v1` overlay.

Forget is not product-complete until I-4E provides loopback API/SOUL Lab UI and I-4F provides production crash/race/security/fresh-conversation validation.

## Ownership boundary

RelayMEM owns memory meaning, lifecycle, source lineage, current-state resolution, mutation identity, deterministic page content, page/index/log semantics, recovery classification, retrieval eligibility, and Secondary MEM meaning.

Phase 6 owns dispatch admission and identity, response-finalization handoff, durable queue lifecycle, claim/lease/retry/terminal control, worker invocation, and restart/checkpoint integration.

I1-G owns durable-finalization evidence, one-record replay, completion, retention classification, isolation, crash validation, and evidence cleanup. O1 owns only bounded scheduling and lane aggregation. B3 owns queue lifecycle. C2 owns one queued-record coordination. C1-2 owns worker execution. RelayCTX owns backend-bound packing. SOUL Lab owns bounded read models and explicit user-operation surfaces without filesystem, queue, scheduler, or worker authority.

## Completed Primary MEM integration

```text
finalized ordinary turn
  -> I1-B request-runtime A1/A2/B1                     complete
  -> C1-5 protected source then B2 queue               complete
  -> B3 queue claim/lease/retry lifecycle              complete
  -> O0 explicit local selection and one C2 call       complete
  -> C2/C1 worker path and verified Primary MEM        complete
  -> later M2 / RelayCTX recall                        complete as I-1
  -> real Lab observation                              complete as I-2
  -> audited correction and corrected retrieval        complete as I-3
  -> canonical read-only lifecycle resolution          complete as I-4B
  -> hidden-successor lifecycle commit                 complete as I-4C1
  -> prepared recovery and tombstone finalization      complete as I-4C2
  -> ordinary retrieval exclusion and lifecycle overlay complete as I-4D
```

## Target migration sequence

```text
I1-GA durable-finalization contract                                  complete
I1-GB durable publication / pre-release evidence admission            complete
I1-GC one-record replay / exact C1-5+B2 / completion                  complete
I1-GD bounded retention / isolation cleanup                           complete
I1-GE validation-only full production crash proof                     complete

I-4A  lifecycle/persistence/concurrency/API/fault contract            defined target
I-4B  current-state resolver/shared Correct/Forget fence              complete
I-4C1 shared revision claim/prepared artifact/hidden successor        complete
I-4C2 exact replay/forward recovery/tombstone                         complete
I-4D  ordinary M2/RelayCTX exclusion/historical projection            complete
I-4E  loopback API and SOUL Lab Forget UI                             unimplemented
I-4F  crash/race/security/fresh-conversation validation               unimplemented

O1A   two-lane round/adapter/idle contract                            complete
O1B   sealed-record discovery/I1-GC delegation                        complete
O1C   B2 discovery/O0-compatible C2 delegation                        complete
O1D1  accepted scheduler gates/one production round                   complete
O1D2  ordering/fairness/retry-time/backoff/jitter/pacing              unimplemented
O1E   stale recovery/cancellation/graceful shutdown                   unimplemented
O1F   full operational validation                                     unimplemented
```

## Completion interpretation

M3a-M3h, B0-B3, C1-0 through C1-5, C2, O0, I1-GA through I1-GE, O1A through O1D1, I-1 recall, I-2 observation, I-3 Correct, I-4B, I-4C1, I-4C2, and I-4D are implemented. O1D1 is a bounded one-round coordinator only; O1D2, O1E, O1F, O2, and O3 remain incomplete. Forget is not product-complete until I-4E and I-4F provide API/UI and production validation.
