---
relaylm_doc_type: implementation_plan
relaylm_authority: phase6_async_relayslp_bounded_slice
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6 RelaySLP slice lands
  - request-runtime enqueue wiring changes
  - queue lifecycle or worker semantics change
  - RelayMEM-M3 producer consumer boundary changes
  - RelayRUN retry checkpoint or idempotency ownership changes
  - I1-G durable-finalization boundary changes
  - O1/O2/O3 operational scheduler boundary changes
  - RT-1 reader or writer cutover decisions change current Primary compatibility meaning
  - RT-1D-R5 or R6 retirement disposition changes
relaylm_not_authoritative_for:
  - repository-wide exact current transaction or phase sequencing
  - RelayMEM candidate semantic classification
  - exact durable MEM page index or log schemas
  - exact RT-1 durable cutover state or R5/R6 retirement approval
  - RelaySOUL approval or revision schemas
  - SOUL Lab runtime TTS audio or avatar execution
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - project_execution_plan.md
  - phase6a1_relayslp_job_admission_contract.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - integration_i1_primary_mem_two_turn_recall.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - o1a_two_lane_scheduler_contract.md
  - o1d1_production_scheduler_round.md
  - o1f_operational_validation.md
  - o2_supervised_scheduler_service.md
  - o3_always_on_local_scheduler.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - relaymem_slp_current_target.md
  - memory_lifecycle_design.md
  - runtime/compile-and-checkpoint.md
  - ../PROJECT_STATUS.md
relaylm_related_contracts:
  - ../contracts/relayrun-checkpoint-and-recovery.md
---
# Phase 6 Asynchronous RelaySLP Bounded Slice

Last reviewed: 2026-08-08 JST

## Status

The bounded Phase 6 RelaySLP execution stack is implemented through I1-B, fenced B3 lifecycle, Phase 6-C1-0 through C1-5, and the bounded Phase 6-C2 one-job adapter. Phase I-1 later completed the historical two-turn Primary MEM recall/isolation proof. I1-GA through I1-GE later completed the pre-enqueue durable-finalization publication/replay/retention/crash-validation boundary. O1/O2/O3 later added bounded and opt-in local scheduler operation through their own authorities.

```text
Phase 6-A0 ownership and sequencing: complete
Phase 6-A1 deferred job admission: complete
Phase 6-A2 response-finalization handoff: complete
Phase 6-B0 durable queue contract: complete
Phase 6-B1 dispatch/job-record preflight: complete
Phase 6-B2 atomic durable enqueue: complete
Phase 6-B3 claim/renew/retry/stale/terminal lifecycle: complete
I1-B request-runtime enqueue/source production: complete
Phase 6-C1-0 protected source: complete
Phase 6-C1-1 M3a-M3h compose: complete
Phase 6-C1-2 one-claimed worker: complete
Phase 6-C1-3 outcome classifier: complete
Phase 6-C1-4 integrated fault smoke: complete
Phase 6-C1-5 durable protected source: complete
Phase 6-C2 one-job claim/rehydrate/execute adapter: complete
Phase I-1 two-turn Primary compatibility recall/isolation proof: complete
I1-GA through I1-GE durable-finalization boundary: complete
O1 bounded scheduler/control stack: complete through O1F
O2 opt-in supervised local scheduler service: complete
O3 opt-in local CLI/process wrapper: complete
```

These completion facts are capability and regression evidence. They are not an unconditional current Primary runtime path after RT-1D-R4.

Ordinary finalized-turn handling can publish protected source and content-free queue evidence without delaying visible output and without carrying a Primary writer decision. A selected queued job reaches Primary worker execution only when the exact RT-1 writer decision carried into C2/C1-2/C1-1 permits mutation. A later ordinary request chooses exactly one reader authority before memory-family access: `primary_only`, `neither`, or `subjective_only`. Historical Phase I-1 proves the retained Primary compatibility path; it does not bypass the current reader decision or create fallback from Subjective retrieval to Primary.

O1 exposes bounded caller-invoked scheduling/control, O2 an opt-in supervised local service, and O3 an opt-in local CLI/process wrapper. They are not app-embedded, browser authority, or default-on memory authority, and none may bypass RT-1 reader/writer decisions.

## Purpose

RelaySLP is the deferred memory compiler. It improves future memory after the normal response path and must not delay or invalidate an already valid visible response.

The implemented compatibility flow is best read as two separately governed domains:

```text
finalized-turn evidence / deferred work
  -> A1 admission
  -> A2 response handoff
  -> B1 dispatch and durable-record candidate
  -> C1-5 protected-source publication
  -> B2 durable enqueue
  -> optional bounded discovery / operational scheduling

selected queued Primary compatibility work
  + exact RT-1 Primary writer decision
  -> rejected: no C2 claim / no C1 worker / no Primary mutation
  -> permitted:
       C2
       -> B3 claim/lease/retry/stale/terminal lifecycle
       -> C1 worker invokes RelayMEM-owned processing
       -> durable Primary compatibility result

later ordinary request
  -> exact RT-1 reader decision
       -> primary_only: retained Primary compatibility retrieval
       -> neither: no ordinary durable-memory retrieval
       -> subjective_only: finalized Subjective retrieval only
```

Source/queue durability and scheduler eligibility preserve evidence/work availability. They do not preserve writer permission or select an ordinary reader.

## Ownership split

### RelayMEM owns memory meaning and persistence

RelayMEM owns candidate meaning, memory kind, safety scope, persistence-policy interpretation, source lineage, memory-write idempotency, deterministic page construction, page/index/log semantics, recovery classification, and Primary-to-Secondary consolidation semantics.

Phase 6 consumes exact RelayMEM artifacts and must not redefine them.

### Phase 6 / RelayRUN owns deferred execution control

Phase 6 owns admission, finalized-response handoff, dispatch identity, durable queue records, enqueue, claim, lease, retry release, stale recovery, terminal state, worker invocation control, content-free status projection, and restart/checkpoint coordination. Later O1/O2/O3 authorities own their bounded operational selection/service layers over those existing controls.

Queue lifecycle and scheduler eligibility are execution-control state, not RT-1 writer authorization.

### RT-1 owns current ordinary reader/writer authority

RT-1 cutover authority determines the exact ordinary reader class and the exact Primary writer decision. Phase 6, RelaySLP, B3 state, C1 source state, scheduler state, retry state, and idempotency records cannot mint, refresh, or restore those permissions.

Once the durable writer chain reaches `primary_writer_fenced`, retained Phase 6 work/evidence cannot revive Primary mutation authority. Once the ordinary reader decision is `subjective_only`, Phase 6 completion evidence cannot restore Primary ordinary retrieval or fallback.

### Protected source owner

The B2/B3 queue record is intentionally content-free. I1-B produces the exact claim-independent protected capture. C1-5 persists it separately before B2 queue publication and rehydrates it after restart. C1-0 binds a fresh source/scope to the exact current claim.

Missing, corrupt, or mismatched source evidence blocks execution. Queue metadata, trace, frontend history, and visible response text are never used to reconstruct protected content.

C1-5 restart completion applies after durable source publication and enqueue and closes the historical Window B source-recovery problem. The separate pre-enqueue Window A was later resolved by completed I1-GA through I1-GE. I1-G remains its own authority for sealed evidence, replay, completion, retention/isolation, and crash validation.

Neither protected-source recovery path carries durable Primary writer permission.

### RelaySLP never mutates SOUL directly

RelaySLP may read SOUL as a protected anchor and may later emit a separately governed proposal. It never writes or applies RelaySOUL directly.

## Implemented boundaries

### A1: deferred job admission

A1 validates trigger, processing stage, correlation, namespace, source lineage, response terminal state, and persistence policy. It performs no queue I/O or memory write.

### A2: response-finalization handoff

A2 consumes the exact A1 result for a finalized `turn_end` and creates a runtime-private enqueue candidate behind explicit gates. It performs no queue I/O or worker execution.

### B0: durable queue contract

B0 defines durable job schema, dispatch-idempotency ownership, state machine, revision/attempt/generation/lease invariants, retry/terminal semantics, restart/corruption behavior, and content-free projections.

### B1: dispatch/job-record preflight

B1 derives deterministic dispatch/job identities and one exact queued record candidate without queue I/O.

### C1-5 and B2 publication order

```text
exact finalized-turn protected capture
  -> durable protected-source create-if-absent
  -> unchanged B2 content-free durable enqueue
  -> optional process-local hot cache
```

An equivalent source artifact is idempotent. Same identity with different protected content is a collision and is never overwritten. This publication path provides evidence/work availability only; it contains no RT-1 writer authorization.

### B3: fenced queue lifecycle

B3 implements:

```text
claim
renew_lease
retry_release
stale_recovery
commit_terminal
```

It provides revision/state/job/dispatch CAS, active owner/generation/token fencing, stale recovery, terminal immutability, nonblocking queue locking, and content-free lifecycle projection. It does not execute RelayMEM, decide memory meaning, or decide RT-1 writer authority.

### C1-0: exact protected source

C1-0 accepts one exact current claimed record and one exact protected capture, validates all correlation, creates a request-local one-shot scope, and emits a runtime-private `relaymem.slp_primary_worker_source.v0`.

A valid C1-0 source is necessary evidence for the historical Primary worker path; it is not writer permission.

### C1-1: RelayMEM composition

C1-1 fixes the exact order:

```text
exact Primary writer-decision gate
  -> M3a -> M3b -> M3c -> M3d -> M3e -> M3f -> M3g -> M3h
```

It remains queue-agnostic and preserves every direct-helper validator. A non-permitted writer decision fails closed before source consumption or M3 execution.

### C1-2: one already-claimed worker

C1-2 accepts the exact caller-carried Primary writer decision and executes one exact active claim only after that decision permits write. It revalidates or renews the B3 lease before source consumption, M3e, M3g, and the final B3 transition. Those checkpoints are lease fences, not cutover-state rereads.

C1-2 owns bounded retry timing for transient lock contention and verified reconciliation partial progress. Corruption, policy hold, manual confirmation, and recovery isolation are not automatically retried. Retry availability does not preserve writer permission.

### C1-3: pure outcome classification

C1-3 maps exact M3e/M3g/M3h evidence to bounded B3 retry or terminal intent without queue, filesystem, clock, random, config, memory, or RT-1 cutover I/O. Writer-decision rejection occurs before this classifier and is not a memory-policy/retry/recovery outcome.

### C1-4: integrated fault smoke

C1-4 verifies normal success, stale claim fencing, lease loss at side-effect boundaries, M3g/M3h lock contention, M3e and reconciliation crash convergence, terminal-commit crash, idempotent new-claim convergence, corruption isolation, and content-free diagnostics for an admitted Primary worker path. Its fault evidence does not grant writer authority.

### C1-5: durable protected source

C1-5 persists the claim-independent capture separately, validates identity and integrity, rehydrates after restart, retains it across retry/stale recovery, and removes it only after canonical terminal commit. The durable artifact intentionally does not store RT-1 writer-decision identity.

### C2: one queued-job integration

C2 accepts one caller-selected exact queued record plus the exact caller-carried Primary writer decision. For an enabled request, a non-permitted decision fails closed before B3 claim, protected-source consumption, or C1 worker invocation. A permitted decision allows C2 to delegate claim mutation to canonical B3, fresh source/scope preparation to C1-5, and execution to C1-2. C2 does not scan or schedule the queue and does not mint cutover authority.

### Phase I-1: historical two-turn Primary compatibility proof

Phase I-1 proves the bounded two-turn connection that originally closed the Primary MEM integration loop:

```text
turn 1
  -> source publication and enqueue
  -> explicit B3 claim
  -> C1-5 rehydrate
  -> C1-2 forms Primary MEM
  -> B3 terminal success

turn 2
  -> existing RelayMEM M2 retrieval
  -> exact character/namespace and page/index/log validation
  -> bounded RelayCTX injection
  -> backend request contains selected memory evidence
  -> backend response uses formed memory
```

The integration verifies character/namespace isolation, duplicate dispatch and retrieval deduplication, restart rehydration, policy blocking, bounded size/token behavior, canonical page/index/log reconciliation, unsafe-path rejection, content-free public diagnostics, and absence of cross-character selection. It does not add run/session as a new long-term retrieval restriction.

Under RT-1D-R4 this remains historical/compatibility evidence. Primary formation in a fresh invocation requires an exact permitted writer decision, and later ordinary Primary retrieval is reachable only under the exact `primary_only` reader decision. `subjective_only` performs no Primary recall/fallback.

### I1-G: pre-enqueue durable-finalization boundary

I1-GA through I1-GE are complete under their canonical contract. Together they provide durable pre-release sealed evidence, caller-selected replay/completion convergence into exact C1-5/B2 state, bounded retention/isolation/cleanup, and real process-exit/fresh-restart validation.

I1-G completion does not imply B3 terminal success, C2/worker execution, Primary formation, current writer permission, current reader permission, or scheduler operation.

### O1/O2/O3: operational scheduling boundary

O1A through O1F provide the bounded scheduler contract, discovery/delegation, one-round coordination, operational control, and validation hardening described by their own authorities. O2 provides an opt-in supervised local scheduler service above O1E; O3 provides an opt-in local CLI/process wrapper around O2.

These layers may select/delegate existing work only through the established authorities. They do not add memory semantics, queue state meanings, RT-1 writer/reader authority, browser authority, or default-on app embedding.

## Remaining / downstream work

The old Phase 6 plan listed scheduler/service lifecycle and the pre-enqueue crash window as later work. Those items were subsequently implemented by O1/O2/O3 and I1-G through separate authorities.

Still-separate target work includes any future Secondary MEM job families after their owning RelayMEM authority, any separately governed RelaySOUL proposal handoff, and future checkpoint/retry/dead-letter or operational refinements only when their own bounded requirements and authorities are approved. This document does not infer that such target work is current or authorized merely because Phase 6 infrastructure exists.

## Idempotency separation

```text
Dispatch idempotency
  owned by Phase 6 / RelayRUN
  prevents duplicate logical queue dispatch

Memory-write idempotency
  owned by RelayMEM
  prevents duplicate durable memory application

Retrieval deduplication identity
  owned by the request-local RelayMEM/RelayCTX integration
  prevents one durable memory from appearing more than once in one prompt
```

A job retry may be valid while an existing memory write remains exact. Dispatch key, lease token, claim generation, memory-write key, and retrieval deduplication identity must not be collapsed. None of these identities is an RT-1 writer or reader authorization token.

## Safety invariants

All Phase 6 slices preserve:

- visible response delivery never waits for SLP completion,
- SLP failure never invalidates an already valid response,
- default-off and dry-run-first rollout where applicable,
- fail-closed schema, namespace, policy, lineage, queue, lease, source, and writer-decision correlation,
- protected content remains outside queue and generic diagnostics,
- public projections remain content-free,
- Primary-layer autonomous formation is possible only when both RelayMEM gates and the exact RT-1 writer decision permit it,
- a durable source, queued job, active lease, retry, scheduler selection, or idempotent state cannot restore writer authority after `primary_writer_fenced`,
- ordinary durable-memory serving resolves exactly one reader authority and never dual-serves or cross-falls back between Primary and Subjective,
- sensitive, contradictory, destructive, cross-namespace, or SOUL-affecting changes remain held or blocked under their owning policies,
- RelaySLP never directly mutates SOUL,
- TTS/audio/avatar execution remains outside RelayLM Core.

## Active completion criterion

The historical Phase 6 bounded execution stack is complete through C1-5/C2, the historical Phase I-1 Primary two-turn compatibility proof is complete, the wider pre-enqueue durability boundary is complete through I1-GA-GE, and bounded/opt-in local scheduling is complete through O1/O2/O3.

Those completed capabilities do not define the current ordinary memory authority after RT-1D-R4. Current Primary mutation remains subordinate to the exact writer decision; current ordinary retrieval remains subordinate to the exact one-reader decision. Phase I-2 observation and Phase I-3 Correct were completed later through their separate authorities and are not Phase 6-owned semantics.

R5/R6 own final retirement or explicitly retained read-only/historical/test disposition of replaced Primary reader, worker, fallback, and temporary cutover surfaces. This Phase 6 plan does not pre-authorize deletion, weaken validators, or move Primary mutation/retrieval authority into RelaySLP or scheduler layers.
