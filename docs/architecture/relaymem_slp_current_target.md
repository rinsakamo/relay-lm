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
  - o1f_operational_validation.md
  - phase_i5b_pin_unpin_apply.md
  - phase_i7c_held_apply_discard_runtime.md
  - e1r1_trusted_home_scene_admission.md
  - e1r2_character_store_bootstrap.md
  - e1r3_provenance_preserving_primary_mem_formation_summary.md
  - phase_i4f_forget_validation.md
  - e1_evaluation_consolidation.md
  - wave6_cross_slice_convergence_audit.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

Last reviewed: 2026-06-28 JST

## Current implemented boundary

RelayMEM currently provides bounded store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, gated RelayCTX injection, auditable Correct, canonical read-only Primary current-state resolution, I-4C1 hidden-successor lifecycle commit ownership, bounded I-4C2 recovery/finalization, I-4D ordinary retrieval lifecycle exclusion plus historical lifecycle overlay, I-4E loopback Forget API/UI, I-4F full Forget validation, I-5A Pin / Unpin read-only preflight, I-5B Pin / Unpin apply/API/UI/ranking behavior, I-7A/B Held Apply / Discard read-only preflight, and I-7C Held Apply / Discard runtime/API/UI/durable governance evidence.

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

Phase 6-B2 performs atomic durable enqueue of durably enqueued jobs through the existing content-free queue record authority. Phase 6-B3 performs default-off, dry-run-first fenced queue lifecycle transitions. C1-2 executes one already-claimed canonical B3 job. C1-5 persists protected content separately from the content-free queue. C2 one-job claim/rehydrate/execute adapter accepts one caller-selected queued record and connects B3 claim, C1-5 preparation, and C1-2 execution. O0 adds bounded discovery and one C2 delegation without polling or retry scheduling.

I2 real SOUL Lab observation is complete. It is read-only evidence only and cannot authorize repair or retrieval.

E1 evaluation consolidation is current as an evidence/documentation boundary. E1-R1 route-owned trusted Home scene admission is current implemented. E1-R2 dry-run-first character-store bootstrap is current implemented. E1-R3 provenance-preserving summary formation is current implemented. E1-R4 evidence-grounded recall behavior remains quality work.

## I1-G durable-finalization boundary

I1-GA through I1-GE are complete. I1-G completion means sealed evidence, exact C1-5 source, exact B2 queue correlation, durable completion, retention/isolation lifecycle, and crash-at-every-boundary validation. It does not imply B3 terminal success, C2 execution, worker execution, Primary MEM formation, semantic quality, retrieval use, automatic scheduling, polling, supervision, or always-on operation.

## O1 scheduler boundary

O1A defines a pure scheduler contract. O1B and O1C bounded production discovery and delegation are complete. O1D1 accepts the five exact scheduler gates, invokes O1B then O1C at most once each, aggregates through O1A, validates the content-free projection, and returns without sleeping.

O1D2 is current implemented as a bounded policy wrapper around the existing O1D1 one-round scheduler coordinator. O1D2 does not poll, sleep, run a second round, recover stale claims, handle cancellation, supervise services, or create a durable scheduler journal.

O1E is current implemented as a bounded caller-invoked operational-control layer. One explicit call may check cancellation, optionally orchestrate at most one B3 stale-recovery transition through existing B3 authority, invoke at most one O1D2/O1D1 scheduler round, and return a bounded content-free projection. O1E does not poll, sleep, loop, daemonize, supervise, create background workers, start timers, or rewrite queue records directly.

O1F is current implemented as validation-only hardening over the caller-invoked O1E/O1D2/O1D1 stack. It validates corruption, concurrency, saturation/boundedness, restart reread, cancellation/shutdown projection, and leakage boundaries. O1F does not poll, sleep, loop, supervise, create workers, or implement O2/O3.

O2 supervision and O3 always-on operation remain unimplemented.

## Current Primary mutation and lifecycle-read boundary

I-4E is current implemented as loopback Forget API/UI.

I-4F is current implemented as validation-only Forget product completion. It proves crash/fault recovery, one-winner races, Correct/Forget stale races, strict token binding, loopback/security leakage boundaries, stale-browser response fencing, no implicit UI apply triggers, fresh process reread, fresh ordinary conversation exclusion, and multi-scope isolation over the existing I-4B/I-4C1/I-4C2/I-4D/I-4E authorities. I-4F does not create new mutation authority.

UI-B1A is current implemented read-only visibility. I-5A is current implemented contract/read-only preflight only. I-5B is current implemented as Pin / Unpin apply/API/UI/ranking behavior. I-7A/B is current implemented contract/read-only preflight only. I-7C is current implemented as Held Apply / Discard runtime/API/UI/durable governance evidence.

I-5B Pin state remains governance metadata and a ranking hint. It never admits hidden, prepared, recovery-required, corrupt, cross-scope, or prior physical revisions. I-7C persists content-free decision evidence for already-held candidates and does not start workers, schedulers, retry loops, C2, O1, or B3 transitions from the UI.

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
  -> full Forget product validation                    complete as I-4F
  -> read-only lifecycle visibility                    complete as UI-B1A
  -> Pin / Unpin read-only preflight                   complete as I-5A
  -> Pin / Unpin apply and ranking hint                complete as I-5B
  -> Held Apply / Discard read-only preflight          complete as I-7A/B
  -> Held Apply / Discard runtime governance           complete as I-7C
  -> E1 evidence consolidation                         complete as E1
  -> route-owned trusted Home admission                complete as E1-R1
  -> dry-run-first character-store bootstrap           complete as E1-R2
  -> provenance-preserving formation summary           complete as E1-R3
  -> bounded scheduler operational controls            complete as O1E
  -> operational validation hardening                  complete as O1F
```

## Completion interpretation

M3a-M3h, B0-B3, C1-0 through C1-5, C2, O0, I1-GA through I1-GE, O1A through O1F, I-1 recall, I-2 observation, I-3 Correct, I-4B, I-4C1, I-4C2, I-4D, I-4E, I-4F, UI-B1A, I-5A, I-5B, I-7A/B, I-7C, E1, E1-R1, E1-R2, and E1-R3 are implemented. O1F is validation-only caller-invoked operational hardening; O2 and O3 remain incomplete. E1-R1 is route-owned and defaults disabled; it does not permit browser-owned trust. E1-R2 is dry-run-first and does not create semantic memory content. E1-R3 is speaker-provenance-safe formation summary work and does not implement retrieval-response grounding. E1-R4 remains incomplete quality/evaluation work.
