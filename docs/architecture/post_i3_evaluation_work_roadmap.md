---
relaylm_doc_type: implementation_plan
relaylm_authority: planned_post_i3_work_and_evaluation_sequence
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - a post-I3 product slice begins or lands
  - SOUL Lab real conversation integration changes state
  - I1-G or worker-service sequencing changes
  - an evaluation gate changes state
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact mutation schemas
  - exact queue or worker contracts
  - RelaySOUL revision schema
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_implementation_plan.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - phase_i4c2_primary_forget_recovery_finalization.md
  - phase_i4d_primary_retrieval_exclusion.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - i1gd_durable_finalization_retention_cleanup.md
  - i1ge_durable_finalization_crash_validation.md
  - o1d1_production_scheduler_round.md
  - wave3_cross_slice_convergence_audit.md
---
# Post-I3 Evaluation and Work Roadmap

Last reviewed: 2026-06-27 JST

## Purpose

Phase I-3 Correct, UI-B0 real Home conversation, O0 local one-job execution, I1-GA through I1-GE, I-4B, I-4C1, I-4C2, I-4D, O1A, O1B, O1C, and O1D1 are complete at their bounded boundaries. Phase I-4A remains the target Forget / Hide contract. I-4E, I-4F, O1D2, O1E, and O1F remain incomplete. W3-INT is merged, and Wave 4 follow-up planning may use the frozen W3-INT authority map and inputs.

This roadmap separates four authorities:

```text
Memory governance
  -> Forget API/UI and validation
  -> Pin, Held review, Merge
  -> Secondary MEM and RelaySOUL

SOUL Lab experience
  -> real Home conversation
  -> read-only lifecycle and operation visibility
  -> repeatable evaluation evidence

Durability
  -> pre-release evidence
  -> one-record restart replay and completion
  -> bounded retention and isolation cleanup
  -> validation-only full crash proof

Operations
  -> O0 one-job execution
  -> O1A round/idle contract
  -> O1B/O1C bounded production lane adapters
  -> O1D1 accepted gates and one production round
  -> O1D2 ordering/fairness/retry-time/backoff/jitter/pacing policy
  -> O1E recovery/cancellation/shutdown
  -> O1F operational validation
  -> O2/O3 supervised and always-on operation
```

## Current completed foundation

Complete:

- ordinary managed Turn 1 Primary MEM formation through C2;
- O0 explicit execution of at most one eligible durable queued job;
- O1A pure replay-before-queue round/idle contract;
- O1B one bounded sealed-record replay-lane adapter;
- O1C one bounded queue-lane adapter;
- O1D1 one accepted-gate replay-before-queue production round;
- next-turn M2 retrieval and RelayCTX injection;
- character and namespace isolation;
- Phase I-2 real read-only Lab observation;
- Phase I-3 auditable Correct and corrected retrieval;
- UI-B0 bounded non-stream and SSE Home conversation;
- I1-GA durable-finalization contract and fault model;
- I1-GB bounded base/segment/seal publication before protected visible release;
- I1-GC one sealed-record replay through exact C1-5/B2/completion;
- I1-GD bounded retention/orphan isolation/marker-last cleanup;
- I1-GE real process-exit/fresh-restart crash validation;
- I-4B shared current-state resolver and mutation fence;
- I-4C1 hidden-successor commit;
- I-4C2 prepared recovery/tombstone finalization;
- I-4D ordinary M2/RelayCTX lifecycle exclusion and historical lifecycle overlay.

## Evaluation interpretation

I1-G overall complete means sealed durable-finalization evidence through exact C1-5/B2 correlation, durable completion, retention/isolation lifecycle, and crash-at-every-boundary validation. It does not imply B3 terminal success, C2 execution, worker execution, Primary MEM formation, semantic quality, retrieval use, automatic scheduling, polling, supervision, or always-on operation.

I-4D complete means ordinary retrieval excludes hidden, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, and prior physical revisions before snippet construction and backend-bound RelayCTX. It does not implement Forget mutation API/UI, restore, purge, physical deletion, or product-level validation. Phase I-4 remains in progress until I-4E and I-4F land.

O1D1 complete means one caller-invoked production round accepts exact server-owned scheduler gates, invokes replay then queue at most once each, aggregates through O1A, and returns without sleep. It does not implement polling, recurring automatic scheduling, fairness, backoff, retry-time policy, stale recovery, shutdown, supervision, or always-on operation. O1 remains in progress.

## Wave 4 start sequence

Current dependency-first follow-up work is:

```text
O1D2 ordering/fairness/retry-time/backoff/jitter/pacing
  -> O1E stale recovery/cancellation/shutdown
  -> O1F operational validation

I-4E loopback API and SOUL Lab Forget UI
  -> I-4F crash/race/security/fresh-conversation validation

UI-B1A read-only lifecycle visibility
I-5A Pin / Unpin contract/preflight
I-7A/B Held Apply / Discard contract/preflight
```

The frozen start contracts are recorded in [Wave 3 Cross-Slice Convergence Audit](wave3_cross_slice_convergence_audit.md).

## Non-goals for the immediate next wave

The next wave must not backfill future production authority into W3-INT. It must not add a scheduler polling loop, sleep, daemon/service supervision, always-on processing, new durable-finalization schema, replay algorithm, queue lifecycle, worker semantic behavior, Primary MEM mutation beyond exact slice ownership, restore/unhide/purge, TTS/audio/avatar/Live2D, ASR, or peer communication.

## Product evaluation sequence

The explicit E1 path is complete across two separate proven lanes:

```text
explicit trusted scene-qualified managed request
  -> O0 one-job execution
  -> Primary MEM formation
  -> Phase I-2 observation
  -> Phase I-3 Correct

Home real conversation
  -> existing M2 / RelayCTX recall
  -> Home New Conversation
  -> corrected-memory question
  -> Phase I-2 used-memory evidence
```

Direct Home-origin formation remains unproven because UI-B0 does not send trusted scene-admission metadata. Repeated automatic operation still depends on O1D2/O1E policy and later O2/O3 service work.
