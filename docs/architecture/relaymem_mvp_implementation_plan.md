---
relaylm_doc_type: implementation_plan
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - RelayMEM MVP slice lands
  - RelaySLP worker sequencing changes
  - memory lifecycle semantics change
  - Lab memory operation API changes
  - O1 scheduling boundary changes
relaylm_not_authoritative_for:
  - repository-wide phase completion status
  - global Phase 5.5 sequencing
  - exact runtime schema details
  - RelaySOUL approval contract details
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_implementation_plan.md
  - post_i3_evaluation_work_roadmap.md
  - relaymem_slp_current_target.md
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
# RelayMEM MVP Implementation Plan

Last reviewed: 2026-06-27 JST

## Purpose

This document owns the RelayMEM MVP implementation track. Repository-wide sequencing remains owned by [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

M3a-M3h, worker execution, durable protected-source recovery, C2 one-job execution, O0 explicit local operation, Phase I-1 recall, Phase I-2 observation, Phase I-3 Correct, I-4B, I-4C1, I-4C2, and I-4D are complete. Phase I-4A defines the target Forget / Hide contract. I-4D is the user-visible retrieval semantic commit, but product-level Forget remains in progress until I-4E API/UI and I-4F validation land.

I1-GA through I1-GE are complete outside RelayMEM lifecycle authority. O1A, O1B, O1C, and O1D1 are complete at their bounded boundaries; O1D2/O1E/O1F and O2/O3 remain operations work.

## Completed product loop

```text
ordinary turn
  -> Primary MEM formation
  -> durable page/index/log result
  -> later-turn retrieval and RelayCTX injection
  -> bounded real Lab observation and observation receipts
  -> explicit Correct
  -> immutable successor revision and audit receipt
  -> later retrieval of corrected current revision
```

## Current implementation position

```text
MEM-M0 lifecycle and terminology: complete baseline; I-4A target defined
MEM-M1 store-layout compatibility/read-only diagnostics: complete
MEM-M2 retrieval priority/snippet/injection foundations: complete for current eligible memory

MEM-M3 Primary MEM path:
  M3a formation candidate: complete
  M3b source lineage and write preflight: complete
  M3c deterministic page candidate: complete
  M3d writer-handoff preflight: complete
  M3e atomic Primary page writer: complete
  M3f index/log reconciliation preflight: complete
  M3g index/log reconciliation apply: complete
  M3h read-only recovery audit: complete
  M3i-a worker contract/fault/restart integration: complete through C1-5
  M3i-b one-job runtime adapter: complete as Phase 6-C2
  O0 explicit local one-job caller: complete
  O1A two-lane round/idle contract: complete
  O1B sealed replay-lane adapter: complete
  O1C queue-lane adapter: complete
  O1D1 accepted gates and one production round: complete
  O1D2/O1E/O1F: unimplemented
  M3i-c next-turn recall and scope isolation: complete as Phase I-1
  M3i-d real read-only Lab observation: complete as Phase I-2
  M3i-e auditable Correct: complete as Phase I-3
  M3i-f canonical current-state resolver/shared fence: complete as Phase I-4B
  M3i-g hidden-successor commit ownership: complete as Phase I-4C1
  M3i-h prepared recovery/M3f-M3g/tombstone finalization: complete as Phase I-4C2
  M3i-i ordinary retrieval exclusion/history projection: complete as Phase I-4D

MEM-M4 Secondary MEM consolidation: deferred

MEM-M5 Lab-ready operations:
  real observation reads: complete as Phase I-2
  auditable Correct: complete as Phase I-3
  Forget / Hide contract: defined target as Phase I-4A
  Forget resolver/shared fence/read-only preflight-token-history: complete as I-4B
  Forget hidden-successor commit: complete as I-4C1
  Forget prepared recovery/M3f-M3g/tombstone/replay: complete as I-4C2
  Forget ordinary retrieval exclusion/history projection: complete as I-4D
  Forget API/UI and full validation: unimplemented as I-4E/I-4F
  Pin/Merge/Held review: later
```

## M2 and I-4D retrieval boundary

M2 supports bounded candidate selection by namespace, layer, scope metadata, summary/tag matching, runtime-private snippet extraction, content-free projection, and gated RelayCTX injection. I-4D now consumes the shared I-4B/I-4C2 current-state authority before snippet construction:

```text
active + mutation none + current physical revision
  + converged controls + valid scope/page -> eligible
hidden                                      -> excluded
prepared or recovery_required               -> excluded fail-closed
corrupt or ambiguous lifecycle chain        -> excluded fail-closed
unsafe or cross-scope candidate              -> excluded fail-closed
prior physical revision                      -> excluded
```

A hidden current successor must never allow fallback to a prior active revision. Historical used-memory evidence is never rewritten; I-4D adds a read-only current lifecycle overlay.

## Independence and integration

```text
Phase 6 owns queue and worker control
I1-G owns pre-release finalization evidence, one-record replay, completion, retention, and crash validation
O1 owns bounded scheduling between replay and queue work sources
RelayMEM owns memory meaning, lifecycle, and persistence
RelayCTX owns later-turn packing
SOUL Lab owns bounded observation and explicit operations through server APIs
```

Replay completion is not memory formation. Queue terminal state is not a semantic quality claim. Retention cleanup is not queue or memory cleanup. RelayMEM lifecycle code must not absorb I1-G, B3, C2, or scheduler authority.

## Completion status

- Primary MEM formation/persistence: complete
- one-job Phase 6 execution: complete
- O0 explicit local one-job caller: complete
- O1A two-lane round/idle contract: complete
- O1B sealed replay-lane adapter: complete
- O1C queue-lane adapter: complete
- O1D1 accepted gates and one production round: complete
- O1D2 scheduling policy, O1E recovery/shutdown, and O1F validation: unimplemented
- I1-GA through I1-GE durable-finalization: complete
- next-turn retrieval and RelayCTX injection: complete
- character/namespace isolation: complete
- real SOUL Lab observation: complete
- auditable Correct: complete
- Phase I-4A Forget / Hide contract: defined target
- Phase I-4B resolver/shared fence/read-only Forget boundary: complete
- I-4C1 hidden-successor commit: complete
- I-4C2 recovery/finalization: complete
- I-4D retrieval exclusion/history projection: complete
- I-4E API/UI and I-4F validation: unimplemented
- Phase I-4 overall: in progress
- Secondary MEM consolidation: deferred

## Sequencing rule

The next RelayMEM governance work after W3-INT merge is:

```text
I-4E API/UI
  -> I-4F validation
```

I-5A Pin / Unpin and I-7A/B Held Apply / Discard contract/preflight work may begin after W3-INT merge as long as they preserve the shared Primary mutation fence and do not add runtime apply behavior beyond their exact slices.

## O1 boundary

O1D1 is one bounded caller-invoked production round. It does not complete polling, recurring automatic processing, fairness, retry-time handling, backoff, jitter, stale recovery, cancellation, graceful shutdown, supervision, or always-on operation. O1 overall remains in progress.
