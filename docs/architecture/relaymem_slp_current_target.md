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
  - E1 evaluation evidence boundary changes
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
  - o1d2_scheduler_policy.md
  - phase_i4e_forget_api_ui.md
  - phase_i5_pin_unpin_contract.md
  - phase_i7ab_held_apply_discard_contract.md
  - e1_evaluation_consolidation.md
  - wave4_cross_slice_convergence_audit.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

Last reviewed: 2026-06-27 JST

## Current implemented boundary

RelayMEM currently provides bounded store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, gated RelayCTX injection, auditable Correct, canonical read-only Primary current-state resolution, I-4C1 hidden-successor lifecycle commit ownership, bounded I-4C2 recovery/finalization, I-4D ordinary retrieval lifecycle exclusion plus historical lifecycle overlay, I-4E loopback Forget API/UI, I-5A Pin / Unpin read-only preflight, and I-7A/B Held Apply / Discard read-only preflight.

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

E1 evaluation consolidation is current as an evidence/documentation boundary. It records that the explicit trusted formation lane can reach durable Primary MEM formation and later Home recall, while Direct Home-origin trusted memory formation remains unimplemented.

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

O1D2 is current implemented as a bounded policy wrapper around the existing O1D1 one-round scheduler coordinator. It adds content-free policy state, deterministic fairness preference hints, retry-window rounding, bounded deterministic jitter without private identity inputs, bounded backoff, and pacing recommendation. O1D2 does not poll, sleep, run a second round, recover stale claims, handle cancellation, supervise services, or create a durable scheduler journal.

O1E stale recovery/cancellation/shutdown, O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented.

The accepted scheduler fields are in `relaylm/config.py`, `docs/config_schema.md`, and `config.example.yaml`:

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

I-4E is current implemented as loopback Forget API/UI. It adds strict SOUL Lab request models, loopback-only preflight/apply/history routes, bounded preflight projection, bounded hidden receipt, SOUL Lab API client, explicit confirmation panel, row-level Forget action, lifecycle refresh, backend functional/security smokes, and browser API/UI smoke. I-4B remains resolver/fence/token/history authority; I-4C1 remains hidden-successor commit authority; I-4C2 remains recovery/tombstone/finalization/public apply authority; I-4D remains ordinary retrieval exclusion authority. I-4F remains target/unimplemented validation.

UI-B1A is current implemented read-only visibility. It provides bounded Primary MEM lifecycle visibility, content-free durable-finalization status visibility, content-free queue/worker status visibility, Home and Lab Observation lifecycle panels, and Fresh Conversation explanation. It adds no mutation or operation-run control.

I-5A is current implemented contract/read-only preflight only. It does not implement Pin apply, Unpin apply, durable Pin state, API/UI, or ranking behavior.

I-7A/B is current implemented contract/read-only preflight only. It does not implement Held Apply runtime, Held Discard runtime, B3 queue mutation, retry release, terminal commit, Primary MEM page/index/log writes, C2 worker invocation, O1 scheduler invocation, or SOUL Lab mutation UI.

## Ownership boundary

RelayMEM owns memory meaning, lifecycle, source lineage, current-state resolution, mutation identity, deterministic page content, page/index/log semantics, recovery classification, retrieval eligibility, and Secondary MEM meaning.

Phase 6 owns dispatch admission and identity, response-finalization handoff, durable queue lifecycle, claim/lease/retry/terminal control, worker invocation, and restart/checkpoint integration.

I1-G owns durable-finalization evidence, one-record replay, completion, retention classification, isolation, crash validation, and evidence cleanup. O1 owns only bounded scheduling and lane aggregation. B3 owns queue lifecycle. C2 owns one queued-record coordination. C1-2 owns worker execution. RelayCTX owns backend-bound packing. SOUL Lab owns bounded read models and explicit user-operation surfaces without storage-root, queue, scheduler, or worker authority.

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
  -> loopback Forget API/UI over existing authorities  complete as I-4E
  -> read-only lifecycle visibility                    complete as UI-B1A
  -> Pin / Unpin read-only preflight                   complete as I-5A
  -> Held Apply / Discard read-only preflight          complete as I-7A/B
  -> E1 evidence consolidation                         complete as E1
```

I2 real SOUL Lab observation is complete. It is read-only evidence only and cannot authorize repair or retrieval. E1 is also read-only/docs-only evidence and cannot authorize Home-origin formation.

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
I-4E  loopback API and SOUL Lab Forget UI                             complete
I-4F  crash/race/security/fresh-conversation validation               unimplemented

I-5A  Pin / Unpin contract and read-only preflight                    complete
I-5B  Pin / Unpin runtime apply/API/UI/ranking work, if defined       unimplemented

I-7A/B Held Apply / Discard contract and read-only preflight          complete
I-7C   Held Apply / Discard runtime/API/UI/evidence work, if defined  unimplemented

O1A   two-lane round/adapter/idle contract                            complete
O1B   sealed-record discovery/I1-GC delegation                        complete
O1C   B2 discovery/O0-compatible C2 delegation                        complete
O1D1  accepted scheduler gates/one production round                   complete
O1D2  ordering/fairness/retry-time/backoff/jitter/pacing              complete
O1E   stale recovery/cancellation/graceful shutdown                   unimplemented
O1F   full operational validation                                     unimplemented

E1    evaluation evidence consolidation                               complete
E1-R1 trusted Home scene-admission path                               unimplemented
E1-R2 idempotent character-store bootstrap command                    unimplemented
E1-R3 provenance-preserving Primary MEM formation summary             unimplemented
E1-R4 retrieval-response grounding and unsupported-detail suppression unimplemented
```

## Completion interpretation

M3a-M3h, B0-B3, C1-0 through C1-5, C2, O0, I1-GA through I1-GE, O1A through O1D2, I-1 recall, I-2 observation, I-3 Correct, I-4B, I-4C1, I-4C2, I-4D, I-4E, UI-B1A, I-5A, I-7A/B, and E1 evaluation consolidation are implemented. E1 is docs/evidence only and adds no runtime behavior. O1D2 is a bounded policy wrapper only; O1E, O1F, O2, and O3 remain incomplete. Forget is not fully validated until I-4F. I-5A does not complete Pin/Unpin runtime apply. I-7A/B does not complete Held Apply/Discard runtime. Direct Home-origin trusted memory formation remains unimplemented.
