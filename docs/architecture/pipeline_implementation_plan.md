---
relaylm_doc_type: implementation_plan
relaylm_authority: implementation_status_and_phase_sequencing
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - phase lands
  - sequencing changes
  - an integration milestone changes state
  - a target-only schema gains producer consumer apply skip block contract projection and smoke coverage
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical MVP authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - current_target_migration_guide.md
  - phase5_5_stream_unpack_bounded_slice.md
  - phase6_async_relayslp_bounded_slice.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - post_i3_evaluation_work_roadmap.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_a7_management_projection_handoff.md
  - soul_lab_runtime_mvp.md
---
# RelayLM Pipeline Implementation Plan

## Purpose

This document owns implementation status, phase sequencing, dependency boundaries, and active integration priorities. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact contracts remain in dedicated documents, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

The project is integration-first. Helper-only or mock-only slices are justified only when they directly unblock an end-to-end milestone or close a demonstrated safety defect.

## Status legend

- **complete**: the bounded contract and intended helper/runtime wiring exist with smoke coverage.
- **defined target**: exact contract exists, but current producers/consumers/apply/UI are not complete.
- **integration pending**: component boundaries exist, but the ordinary runtime does not complete the intended loop.
- **planned**: work is sequenced but exact implementation is not complete.
- **deferred**: intentionally not a gate for the active milestone.

## Current position

```text
Phase 5-C managed-route correctness: complete through bounded v0/v1 apply and C5 plumbing
Phase 5-D pre-stream hardening: complete through D2
Phase 5.5 Stream Unpack / TTS handoff: complete for RelayLM Core; concrete adapter/TTS/audio/avatar pending

Phase 6 asynchronous RelaySLP orchestration:
  A0 through A2: complete
  B0 through B3: complete
  I1-B ordinary request-runtime enqueue/source capture: complete
  C1-0 through C1-5: complete
  Phase 6-C2 one-job claim/rehydrate/execute adapter: complete

RelayMEM Primary integration:
  M1/M2 store and retrieval foundations: complete
  M3a-M3h formation/persistence primitives: complete
  I1 next-turn recall and character/namespace isolation: complete
  I3 auditable Correct and later corrected retrieval: complete
  I4A Forget / Hide exact contract: defined target
  I4B-I4F Forget runtime, M2 exclusion, UI, and validation: unimplemented
  I1-G pre-enqueue background-finalizer durability: unresolved

SOUL Lab:
  UI-A0 through UI-A7: complete
  I2 real latest-run and memory observation: complete
  I3 auditable Primary MEM Correct: complete
  UI-B0 real Home conversation: planned
  Forget UI and broader authoritative mutations: planned

Operations:
  O0 local one-job runner: planned
  O1 queue scanner / retry scheduler: planned
  O2 supervised worker service: planned
  O3 always-on local operation: planned
```

## Compatibility status anchors

Phase 6-B1 dispatch preflight, B2 atomic durable enqueue, and B3 fenced queue lifecycle are complete. Integration Milestone I1-B ordinary managed non-stream/stream deferred enqueue is complete.

Phase 6-C1-0 through C1-5 are complete:

- exact current-claim protected source,
- canonical M3a-M3h composition,
- one-active-claim execution,
- pure outcome classification,
- integrated crash/fault convergence,
- durable claim-independent protected capture and restart rehydration.

Phase 6-C2 one-job claim/rehydrate/execute adapter is complete. It accepts one caller-selected canonical queued record, uses B3 claim, resolves source through C1-5, invokes C1-2, and preserves retry/terminal behavior without adding queue scanning or daemon ownership.

Phase I-1 recall, Phase I-2 observation, and Phase I-3 Correct are complete. Phase I-4A defines the target Forget lifecycle contract only. Detailed post-I3 sequence remains in [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md).

## Completed Primary MEM end-to-end loop

```text
finalized user turn
  -> deferred SLP admission and durable enqueue       complete as I1-B
  -> durable protected source publication             complete as C1-5
  -> B3 queue claim and active lease                  complete helper boundary
  -> C2 one-job claim/rehydrate/execute adapter        complete
  -> exact C1-0 protected source                      complete
  -> C1-2 one-claimed worker execution                complete
  -> C1-1 RelayMEM M3a-M3h processing                 complete
  -> C1-3 outcome classification                      complete
  -> C1-4 fault/crash convergence                     complete
  -> B3 retry release or terminal commit              complete
  -> durable page/index/log result                    complete
  -> next-turn RelayMEM retrieval                      complete as Phase I-1
  -> RelayCTX bounded injection                        complete as Phase I-1
  -> real Lab observation                              complete as Phase I-2
  -> auditable correction and corrected retrieval      complete as Phase I-3
```

Phase I-4A does not extend this runtime completion claim.

### I1-A: B3 queue lifecycle — complete

B3 implements claim, lease renewal, retry release, stale recovery, and terminal commit. It owns queue control only and never schedules or executes a worker by itself.

### I1-B: request-runtime deferred enqueue — complete

Ordinary managed non-stream and stream finalization runs A1 -> A2 -> B1 -> B2 after visible response delivery. It does not claim or execute work inline. C1-5 commits protected source before B2 queue publication for work that reaches the background finalizer.

C1-5 does not close the earlier process-exit window before source publication and B2 enqueue; that is I1-G.

### I1-C: Primary MEM worker and C2 integration — complete

```text
one exact queued canonical B3 record
  -> canonical B3 claim
  -> C1-5 protected capture lookup
  -> fresh C1-0 source and one-shot scope
  -> C1-2 one-claimed worker
  -> canonical B3 retry release or terminal commit
```

The C2 adapter does not scan the queue, own a daemon lifecycle, create a worker pool, sleep until retry time, or redefine RelayMEM semantics.

### I1-D: next-turn recall validation — complete

Phase I-1 proves durable Primary MEM discovery through existing M2, canonical page/index/log validation, exact character partition and namespace isolation, bounded RelayCTX injection, backend-bound inclusion, completed generation, and wrong-scope exclusion.

### I1-E / Phase I-2: real SOUL Lab observation — complete

Phase I-2 exposes bounded, loopback-only latest-run, formed, held/blocked, and actually injected memory evidence without changing RelayMEM, RelaySLP, RelayRUN, or RelayCTX authority.

### I1-F / Phase I-3: auditable Primary MEM Correct — complete

```text
real formed Primary MEM observation
  -> read-only correction preflight and bounded semantic diff
  -> explicit short-lived-token apply
  -> immutable successor page through M3e
  -> M3f/M3g index/log convergence and bounded recovery
  -> immutable correction receipt
  -> existing M2 and RelayCTX select the corrected current revision
```

Phase I-3 preserves stable logical identity, exact scope/revision fencing, one-winner concurrency, idempotent replay, prior-page auditability, historical used-memory integrity, and no correction-specific retriever.

Authority: [Phase I-3 Auditable Primary MEM Correct](phase_i3_auditable_primary_mem_correct.md).

### I1-F2 / Phase I-4A: Primary MEM Forget / Hide contract — defined target

The target contract defines:

```text
Forget                 user-facing operation
hidden                 canonical current retrieval-ineligible lifecycle state
Forget tombstone       immutable runtime-private audit artifact
Candidate A            immutable hidden successor page with revision N+1
```

The hidden successor page, not an independently updated sidecar flag, will be the lifecycle authority. Correct and Forget will share one per-memory revision fence and one canonical current-state resolver. Prepared/recovery/corrupt states will be excluded from normal retrieval.

This phase contains no production route, schema consumer, lifecycle apply, M2 change, or frontend implementation. Exact authority: [Phase I-4A Primary MEM Forget / Hide Contract](phase_i4_primary_mem_forget_hide_contract.md).

### I1-G: pre-enqueue background-finalizer durability — unresolved

I1-G tracks termination after visible response delivery but before durable source and B2 queue publication. C1-5, C2, I-1, I-2, I-3, and I-4A do not close it. `docs/config_schema.md`, the Current/Target matrix, and status smokes must move together; stale TODO or future-tense text in related documents is rejected.

## Phase I-4 implementation sequence

```text
I-4A  exact Forget / hidden / tombstone contract                              defined target
I-4B  canonical resolver, shared Correct/Forget fence, preflight/history      next implementation slice
I-4C  immutable hidden successor, prepared artifact, tombstone, replay         unimplemented
I-4D  index/log convergence, M2 exclusion, historical lifecycle projection    unimplemented
I-4E  loopback wrapper and SOUL Lab Forget UI                                  unimplemented
I-4F  fault, security, race, and fresh-conversation exclusion smoke             unimplemented
```

I-4B may narrow-refactor the correction-specific resolver into a common current-state resolver. It must not become a broad generic memory-mutation framework.

## Planned work after Phase I-4A

```text
Memory governance:
  I-4B through I-4F Forget implementation
  I-5 Pin / Unpin
  I-6 Merge / Supersession
  I-7 Held Apply / Discard
  I-8 Secondary MEM consolidation
  I-9 RelaySOUL proposal / intervention / rollback

SOUL Lab experience:
  UI-B0 Real Home Conversation
  UI-B1 Memory lifecycle visibility
  UI-B2 Evaluation scenarios and evidence

Operations:
  O0 Local one-job runner
  I1-G Pre-enqueue durability
  O1 Queue scanner / retry scheduler
  O2 Supervised worker service
  O3 Always-on local operation
```

UI-B0, O0, and I1-G work may continue in parallel. I-4A does not mark any of them implemented.

## Current completion criteria

The Primary MEM loop is complete through auditable correction when ordinary queued work reaches C1-2 through C2, C1-5 restores protected source for durably enqueued work, later M2/RelayCTX retrieval is scoped, Lab observation is real and restart-readable, and one formed memory can be revision-fenced, corrected, reconciled, audited, and later retrieved as the current revision.

Forget product completion additionally requires I-4B through I-4F. A contract file alone does not satisfy it.

## Current caveats

- Managed client-history exclusion remains default-off and dry-run-only by default.
- RelayLM Core does not execute TTS/audio/avatar behavior.
- I1-G remains unresolved.
- C1-5 protects only work that reached source publication and durable enqueue.
- Phase I-4A implements no runtime Forget path.
- Physical deletion, restore/unhide, Pin, Merge, Held review, Secondary MEM, and RelaySOUL apply/rollback remain outside I-4A.
- Real SOUL Lab Home conversation, local automatic worker selection, queue scanner / daemon operation, and supervised service lifecycle remain planned.
