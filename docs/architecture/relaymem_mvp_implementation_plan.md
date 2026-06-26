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
  - i1g_pre_enqueue_durable_finalization_contract.md
  - i1gd_durable_finalization_retention_cleanup.md
---
# RelayMEM MVP Implementation Plan

Last reviewed: 2026-06-26 JST

## Purpose

This document owns the RelayMEM MVP implementation track. Repository-wide sequencing remains owned by [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

M3a-M3h, worker execution, durable protected-source recovery, C2 one-job execution, O0 explicit local operation, Phase I-1 recall, Phase I-2 observation, Phase I-3 Correct, I-4B, and I-4C1 are complete. Phase I-4A defines the target Forget / Hide contract. The next RelayMEM governance implementation slice is I-4C2, not product-level Forget completion.

I1-GC one-record replay and completion convergence is complete outside RelayMEM lifecycle authority. I1-GD bounded retention and isolation cleanup is also complete outside RelayMEM lifecycle authority. I1-GE and O1B through O1F remain operations work.

## Core lifecycle

```text
Short-term CTX
  -> governed experience evidence
  -> Primary MEM / Experience MEM
  -> RelaySLP consolidation
  -> Secondary MEM / Crystallized MEM
  -> SOUL Lab observation and explicit governed operations
```

Completed product loop:

```text
ordinary turn
  -> autonomous safe Primary MEM formation
  -> durable page/index/log result
  -> later-turn retrieval and RelayCTX injection
  -> bounded real Lab observation
  -> explicit Correct
  -> immutable successor revision and audit receipt
  -> later retrieval of corrected current revision
```

Target Forget loop:

```text
current active Primary MEM
  -> I-4B read-only current-state resolution and preflight
  -> I-4C1 prepared evidence and hidden-successor M3e commit
  -> I-4C2 resume/replay/recovery/tombstone
  -> I-4D index/log and M2/RelayCTX exclusion convergence
  -> I-4E loopback API and SOUL Lab UI
  -> I-4F fresh-conversation and crash/race/security proof
```

## Current implementation position

```text
MEM-M0 lifecycle and terminology: complete baseline; I-4A target defined
MEM-M1 store-layout compatibility/read-only diagnostics: complete
MEM-M2 retrieval priority/snippet/injection foundations: complete for active current memory

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
  O1A two-lane round/idle contract: complete; no production scheduler
  M3i-c next-turn recall and scope isolation: complete as Phase I-1
  M3i-d real read-only Lab observation: complete as Phase I-2
  M3i-e auditable Correct: complete as Phase I-3
  M3i-f canonical current-state resolver/shared fence: complete as Phase I-4B
  M3i-g hidden-successor commit ownership: complete as Phase I-4C1

MEM-M4 Secondary MEM consolidation: deferred

MEM-M5 Lab-ready operations:
  real observation reads: complete as Phase I-2
  auditable Correct: complete as Phase I-3
  Forget / Hide contract: defined target as Phase I-4A
  Forget resolver/shared fence/read-only preflight-token-history: complete as I-4B
  Forget hidden-successor commit: complete as I-4C1
  Forget recovery/tombstone/M2/UI/full validation: unimplemented as I-4C2 through I-4F
  Pin/Merge/Held review: later
```

## Independence and integration

```text
Phase 6 owns queue and worker control
I1-G owns pre-release finalization evidence, one-record replay, completion, retention
O1 owns bounded scheduling between replay and queue work sources
RelayMEM owns memory meaning, lifecycle, and persistence
RelayCTX owns later-turn packing
SOUL Lab owns bounded observation and explicit operations through server APIs
```

Replay completion is not memory formation. Queue terminal state is not a semantic quality claim. Retention cleanup is not queue or memory cleanup. RelayMEM lifecycle code must not absorb I1-G, B3, C2, or scheduler authority.

## MEM-M1: Store contract — complete

The local file-backed store recognizes Primary/Secondary classes, bounded paths, layer/scope/lineage metadata, index/log controls, layout compatibility, secure traversal, bounded scans/reads, UTF-8 validation, and content-free diagnostics.

Observation receipts, correction artifacts, current-state operation evidence, Forget prepared evidence, and future tombstones remain runtime-private non-candidates.

## MEM-M2: Retrieval foundation — complete for active current memory

M2 supports bounded candidate selection by namespace, layer, scope metadata, summary/tag matching, runtime-private snippet extraction, content-free projection, and gated RelayCTX injection.

Authority order remains:

```text
SOUL / OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  > Secondary MEM
  > RelaySCN
  > Primary MEM
  > Short-term CTX
  > latest input
```

I-4B adds the canonical read-only current-state resolver and I-4C1 adds committed hidden lifecycle evidence while preserving current M2 behavior. I-4D must integrate lifecycle eligibility:

```text
active + converged + valid scope/page/controls -> eligible
hidden                                     -> excluded
prepared or recovery_required              -> excluded fail-closed
corrupt or ambiguous lifecycle chain       -> excluded fail-closed
prior physical revision                    -> excluded
```

No production hidden-state filtering exists yet because I-4D integration is not implemented.

## MEM-M3: Formation and persistence — complete

M3a-M3d provide governed input validation, safety classification, RelaySCN policy use, bounded RelayEMO salience, lineage, memory-write idempotency, deterministic page construction, and exact writer handoff.

M3e publishes one exact Primary page with no-clobber secure publication and immediate revalidation. M3f/M3g derive and apply canonical index-before-log reconciliation. M3h audits receipt/store convergence read-only.

## MEM-M3i: Runtime integration — complete through I-4C1

Completed integration includes:

- exact worker-to-M3a evidence;
- dispatch/memory idempotency separation;
- lease-fenced one-claim execution;
- crash/lock/stale/corrupt convergence;
- durable protected-source restart rehydration;
- one-job C2 and O0 invocation;
- later-turn scoped recall and RelayCTX injection;
- real read-only Lab observation;
- auditable Correct and corrected retrieval;
- canonical current-state resolution and shared Correct/Forget fence;
- exact Forget prepared artifact and deterministic hidden-successor M3e commit.

C2 and O0 do not schedule continuously. O1A changes no RelayMEM production behavior. I1-GD removes only expired durable-finalization evidence under its own isolation authority and does not touch RelayMEM pages, indexes, logs, or operation artifacts.

## MEM-M5: Lab-ready operations

### Read surface — complete as Phase I-2

The read surface observes current runtime evidence. It does not create, replace, hide, pin, merge, repair, schedule, or execute memory. Lab observation receipts are secondary read-only evidence only.

### Correct — complete as Phase I-3

Correct provides exact scope/current-revision validation, bounded semantic diff, short-lived token, immutable successor page, M3f/M3g convergence, immutable correction receipt, recovery, exact replay, and later M2 resolution of only the corrected current revision.

### Forget / Hide target — Phase I-4A

```text
Forget            user-facing explicit operation
hidden            canonical current retrieval-ineligible lifecycle state
Forget tombstone  immutable runtime-private audit/recovery artifact
```

### I-4B read-only boundary — complete

I-4B provides stable logical/current physical identity, current revision/lifecycle/mutation/retrieval eligibility, page/control validation, reuse of the existing `.lock`, read-only preflight, five-minute exact-binding token validation, bounded zero-item history, and fail-closed `recovery_required` handling.

### I-4C1 hidden-successor commit — complete

I-4C1 revalidates the exact token and reason under the shared lock, publishes immutable `relaylm.mem.forget_prepared.v0`, constructs deterministic `relaymem.primary_lifecycle_page.v0`, delegates publication to M3c/M3d/M3e, canonically rereads the page, and resolves `hidden / recovery_required / false`.

### Remaining I-4 slices

```text
I-4C2  exact replay, prepared resume, forward recovery,
        tombstone finalization, response-loss convergence
I-4D   index/log convergence, M2/RelayCTX exclusion,
        historical lifecycle projection
I-4E   loopback API and SOUL Lab Forget UI
I-4F   crash/race/security/fresh-conversation validation
```

I-4D is the user-visible semantic commit. I-4C1 does not claim product-level Forget completion.

## I1-G and O1 boundary

I1-GA through I1-GD are complete. I1-GC converges one caller-selected sealed record through exact reconstruction, existing A1/A2/B1, exact C1-5, exact B2, downstream reread, and immutable completion. I1-GD applies bounded retention, content-free isolation, and marker-last cleanup without mutating downstream queue/source/memory authorities. I1-GE full crash validation remains incomplete.

O1A defines a pure replay-before-queue round with at most one future I1-GC delegation and at most one future C2 delegation. O1B through O1F remain unimplemented. Replay output is never a direct queue/C2 input.

## Safety invariants

All RelayMEM slices preserve source lineage, exact character/namespace isolation, bounded content, fail-closed corruption handling, separate idempotency domains, explicit user action for lifecycle mutation, no authority inversion over Secondary/SOUL, no generic trace leakage, and no direct RelaySOUL mutation.

For Forget:

- hidden lifecycle commit never rolls back to active because HTTP or audit finalization failed;
- prepared/recovery/corrupt state remains retrieval-ineligible;
- exact replay creates no new revision or tombstone;
- historical used-memory evidence is never rewritten;
- Forget is not legal erasure or physical deletion.

For I1-GD:

- sealed-pending records are retained regardless of age;
- isolation is durable and canonically reread before component reclamation;
- the isolation marker is deleted last;
- C1-5, B2, B3, C2, worker, and M3 are never mutated.

## Sequencing rule

The next RelayMEM governance work is:

```text
I-4C2 prepared resume / recovery / tombstone
  -> I-4D M2 and RelayCTX exclusion
  -> I-4E API/UI
  -> I-4F validation
```

Parallel non-RelayMEM operations work may proceed as O1B/O1C and I1-GE without moving their authorities into lifecycle code.

## Completion status

- Primary MEM formation/persistence: complete
- one-job Phase 6 execution: complete
- O0 explicit local one-job caller: complete
- O1A two-lane round/idle contract: complete
- O1B through O1F production scheduling: unimplemented
- I1-GC one-record replay and completion convergence: complete
- I1-GD bounded retention and isolation cleanup: complete
- I1-GE full production crash validation: unimplemented
- next-turn retrieval and RelayCTX injection: complete
- character/namespace isolation: complete
- real SOUL Lab observation: complete
- auditable Correct: complete
- Phase I-4A Forget / Hide contract: defined target
- Phase I-4B resolver/shared fence/read-only Forget boundary: complete
- I-4C1 hidden-successor commit: complete
- I-4C2 through I-4F: unimplemented
- Secondary MEM consolidation: deferred
