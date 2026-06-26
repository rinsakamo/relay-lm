---
relaylm_doc_type: implementation_plan
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - RelayMEM MVP slice lands
  - RelaySLP worker sequencing changes
  - memory lifecycle layer semantics change
  - Lab memory operation API changes
  - O1 scheduling boundary changes
relaylm_not_authoritative_for:
  - repository-wide phase completion status
  - global Phase 5.5 sequencing
  - exact RelayMEM runtime schema details
  - RelaySOUL approval contract details
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_implementation_plan.md
  - post_i3_evaluation_work_roadmap.md
  - memory_lifecycle_design.md
  - relaymem_mvp_design.md
  - relaymem_slp_execution_design.md
  - relaymem_slp_current_target.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - o0_local_one_job_runner.md
  - o1a_two_lane_scheduler_contract.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - context_packing_design.md
---
# RelayMEM MVP Implementation Plan

Last reviewed: 2026-06-26 JST

## Purpose

This document owns the RelayMEM MVP implementation track. Repository-wide sequencing remains owned by [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

M3a-M3h, worker execution, protected-source restart recovery, C2 one-job execution, O0 explicit local operation, Phase I-1 recall, Phase I-2 observation, Phase I-3 Correct, the I-4B read-only resolver/shared-fence boundary, and I-4C1 hidden-successor commit are complete. Phase I-4A defines the target Forget / Hide contract. The next RelayMEM governance implementation slice is I-4C2, not product-level Forget completion.

O1A is complete only as a pure two-lane scheduling/idle contract. It changes no RelayMEM production behavior. O1B through O1F discovery, delegation, fairness, recovery, shutdown, and operational validation remain outside the completed RelayMEM path.

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
  -> I-4C1 token-gated prepared evidence and hidden-successor M3e commit
  -> I-4C2 resume/replay/recovery/tombstone
  -> I-4D index/log and M2/RelayCTX exclusion convergence
  -> I-4E user-facing loopback API and SOUL Lab UI
  -> I-4F fresh-conversation and crash/race/security proof
```

Target automatic work loop remains separate:

```text
O1A contract complete
  -> O1B one sealed I1-G discovery and I1-GC delegation
  -> O1C one queued B2 discovery and C2 delegation
  -> O1D ordering/fairness/retry/backoff
  -> O1E stale recovery/cancellation/shutdown
  -> O1F operational proof
```

## Current implementation position

```text
MEM-M0 lifecycle and terminology: complete baseline; I-4A target lifecycle defined
MEM-M1 store-layout compatibility/read-only diagnostics: complete
MEM-M2 retrieval priority/snippet/injection foundations: complete

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

MEM-M5 Lab-ready memory operations:
  real observation reads: complete as Phase I-2
  auditable Correct: complete as Phase I-3
  Forget / Hide contract: defined target as Phase I-4A
  Forget resolver/shared fence/read-only preflight-token-history: complete as I-4B
  Forget hidden-successor commit: complete as I-4C1
  Forget resume/replay/tombstone/M2/UI/full validation: unimplemented as I-4C2 through I-4F
  Pin/Merge/Held review: later
```

## Independence and integration

```text
Phase 6 owns queue and worker control
O1 owns only bounded scheduling between finalization-replay and queue work sources
RelayMEM owns memory meaning, lifecycle, and persistence
RelayCTX owns later-turn packing
SOUL Lab owns bounded observation and explicit operations through server APIs
```

RelayMEM may evolve independently from TTS, Live2D, and Runtime adapter delivery, but runtime wiring and retrieval convergence remain mandatory for completion claims.

O1A does not absorb RelayMEM formation or lifecycle semantics. Replay completion is not memory formation; queue terminal state is not a semantic quality claim.

## Current non-goals

The completed I-4C1 commit boundary does not implement:

- prepared-operation resume, exact applied-result replay, or response-loss convergence;
- a Forget tombstone or forward recovery beyond the M3e commit;
- M2 or RelayCTX hidden-state exclusion;
- a loopback mutation route or SOUL Lab Forget UI;
- physical deletion, secure erase, purge, restore, or unhide;
- Pin, Merge, Held review, Secondary MEM consolidation, or RelaySOUL mutation;
- queue scheduling, daemon, supervised lifecycle, TTS, or Live2D execution.

The completed O1A contract does not implement:

- sealed-record or queue-directory scanning;
- I1-GC or C2 production invocation;
- polling, sleeping, retry-time calculation, backoff, jitter, or fairness;
- stale-claim recovery, cancellation, or graceful shutdown;
- scheduler configuration fields or CLI commands;
- a daemon, worker service, worker pool, or browser scheduler control.

## MEM-M1: Store contract — complete

The local file-backed store recognizes Primary/Secondary classes, bounded paths, layer/scope/lineage metadata, index/log controls, layout compatibility, secure traversal, bounded scans/reads, UTF-8 validation, and content-free diagnostics.

```text
memory/
  sources/
  mem/
    primary/
    secondary/
    index.md
    log.md
```

Phase I-2 observation receipts, correction artifacts, current-state operation evidence, and the current Forget prepared artifact remain runtime-private non-candidates; the future Forget tombstone remains runtime-private as well.

## MEM-M2: Retrieval foundation — complete for active current memory

M2 supports bounded candidate selection by namespace, layer, scope metadata, and summary/tag matching; runtime-private snippet extraction; content-free projection; and gated RelayCTX injection.

Authority order remains:

```text
SOUL / OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  > Secondary MEM
  > RelaySCN
  > Primary MEM
  > Short-term CTX
  > latest input
```

Phase I-4B adds the canonical read-only Primary current-state resolver and I-4C1 adds committed hidden lifecycle evidence while preserving current M2 behavior and Phase I-3 Correct compatibility. I-4D must consume lifecycle eligibility so hidden, prepared, recovery-required, corrupt, and prior physical revisions are excluded consistently from M2 and RelayCTX.

Target eligibility:

```text
active + converged + valid scope/page/controls -> eligible
hidden                                     -> excluded
prepared or recovery_required              -> excluded fail-closed
corrupt or ambiguous lifecycle chain       -> excluded fail-closed
prior physical revision                    -> excluded
```

No production hidden-state filtering exists yet because I-4D integration is not implemented, even though I-4C1 can now durably commit the hidden lifecycle page.

## MEM-M3: Formation and persistence — complete

M3a-M3d provide governed input validation, safety classification, RelaySCN policy use, bounded RelayEMO salience, lineage, memory-write idempotency, deterministic page construction, and exact writer handoff.

M3e publishes one exact selected Primary page with no-clobber secure publication and immediate revalidation. M3f/M3g derive and apply canonical index-before-log reconciliation. M3h audits exact receipt/store convergence read-only.

## MEM-M3i: Runtime integration — complete through I-4C1 hidden lifecycle commit

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
- canonical read-only current-state resolution and shared Correct/Forget fence;
- exact Forget prepared artifact and deterministic hidden-successor M3e commit.

C2 and O0 do not scan continuously, schedule retries, supervise workers, or own RelayMEM lifecycle semantics. O1A does not change this implemented path.

## MEM-M5: Lab-ready operations

### Read surface — complete as Phase I-2

The read surface observes current runtime evidence. It does not create, replace, hide, pin, merge, apply, discard, repair, schedule, or execute memory.

### Correct — complete as Phase I-3

Correct provides exact scope/current-revision validation, bounded semantic diff, short-lived token, immutable successor page, M3f/M3g convergence, immutable correction receipt, recovery, exact replay, and later M2 resolution of only the corrected current revision.

Past used-memory evidence preserves the representation actually injected for that run.

### Forget / Hide target — Phase I-4A

```text
Forget            user-facing explicit operation
hidden            canonical current retrieval-ineligible lifecycle state
Forget tombstone  immutable runtime-private audit/recovery artifact
```

The hidden successor page is lifecycle authority. The tombstone is audit/recovery evidence.

### I-4B read-only boundary — complete

I-4B provides:

- stable logical and exact current physical identity;
- current revision, lifecycle state, mutation state, and retrieval eligibility;
- validated page/control status with bounded content-free reasons;
- reuse of the existing Phase I-3 `.lock` path;
- read-only Forget preflight;
- canonical five-minute exact-binding token validation;
- bounded zero-item history;
- fail-closed `recovery_required` handling.

It performs no Forget lifecycle write and changes no ordinary M2, RelayCTX, or browser behavior.

### I-4C1 hidden-successor commit — complete

I-4C1 revalidates the exact token and bounded reason under the shared lock, claims one revision, publishes immutable `relaylm.mem.forget_prepared.v0`, constructs deterministic `relaymem.primary_lifecycle_page.v0`, passes through M3c/M3d/M3e, canonically rereads the page, and resolves `hidden / recovery_required / false`. It does not run M3f/M3g, finalize a tombstone, resume a prepared operation, or change M2.

### Remaining I-4 slices

```text
I-4C1  token/fence/revision ownership, prepared artifact,
       hidden successor and M3e publication — complete
I-4C2  exact replay, prepared resume, forward recovery,
       tombstone finalization and response-loss convergence
I-4D   index/log convergence, M2/RelayCTX exclusion,
       historical lifecycle projection
I-4E   loopback API and SOUL Lab Forget UI
I-4F   crash/race/security/fresh-conversation validation
```

I-4D is the user-visible semantic commit. I-4C must not claim product-level Forget completion.

## O1A scheduler contract boundary

O1A defines two explicit lane-result types and one deterministic round aggregation:

```text
replay lane
  -> at most one future O1-GC delegation
  -> C1-5/B2/I1-G completion only

queue lane
  -> at most one future C2 delegation
  -> B3/C1-5/C1-2/M3 execution authority unchanged
```

The v0 order is replay then queue. One lane's bounded failure does not automatically suppress the unrelated lane. Scheduler-level invalid gates, unsupported schema, unsafe shared configuration, or missing required capability stop before lane invocation.

O1A public projection contains only bounded statuses, selection/delegation/completion booleans, work-unit counts, disposition hints, retryable/unsafe booleans, and reason IDs. It excludes memory content, source content, identities, paths, claims, exact timestamps, digests, raw exceptions, and nested delegate results.

## Safety invariants

All RelayMEM slices preserve source lineage, exact character/namespace isolation, bounded content, fail-closed corruption handling, separate idempotency domains, autonomous ordinary memory only when gates pass, explicit user action for destructive lifecycle operations, no authority inversion over Secondary/SOUL, no generic trace leakage, and no direct RelaySOUL mutation.

For Forget specifically:

- a hidden lifecycle commit never rolls back to active because audit or HTTP finalization failed;
- prepared/recovery/corrupt state never exposes memory to ordinary retrieval;
- exact replay creates no new revision or tombstone;
- historical used-memory receipts are never rewritten;
- Forget is not a legal-erasure or physical-deletion claim.

For O1A specifically:

- scheduler round aggregation creates no record, job, dispatch, claim, memory, or retry identity;
- replay never executes a worker;
- queue never mutates I1-G evidence;
- replay output is never a direct queue/C2 input;
- disabled and invalid modes invoke no lane;
- dry-run cannot elevate lower authorities to apply;
- no-work never starts a busy loop.

## Sequencing rule

With Correct, I-4A, and I-4B complete, I-4C1 is the next bounded RelayMEM governance implementation slice. It must consume the shared resolver and existing per-memory `.lock` without broadening into a generic mutation framework.

The next parallel work is:

```text
I1-GC one-record replay and completion convergence
|| I-4C1 hidden-successor commit ownership
|| O1B/O1C production lane implementation after O1A contract
```

O1D through O1F remain later operational slices and must not be pulled into RelayMEM lifecycle code.

## Completion status

- Primary MEM formation/persistence: complete
- one-job Phase 6 execution: complete
- O0 explicit local one-job caller: complete
- O1A two-lane round/idle contract: complete
- O1B through O1F production scheduling: unimplemented
- next-turn retrieval and RelayCTX injection: complete
- character/namespace isolation: complete
- real SOUL Lab observation: complete
- auditable Correct: complete
- Phase I-4A Forget / Hide contract: defined target
- Phase I-4B resolver/shared fence/read-only Forget boundary: complete
- I-4C through I-4F production hidden apply, M2 exclusion, UI, and validation: unimplemented
- Secondary MEM consolidation: deferred

## I1-G boundary

I1-GA and I1-GB are complete. I1-GC replay/completion, I1-GD cleanup, and I1-GE full crash validation remain unimplemented. RelayMEM lifecycle work must not absorb I1-G durable-finalization or O1 scheduling authority. O1A defines only how future lane outcomes are bounded and aggregated.

## I1-GC durable-finalization replay current boundary (2026-06-26)

Completed dependency edge:

```text
I1-GA contract
  -> I1-GB pre-release sealed publication
  -> I1-GC one-record restart replay and completion convergence  [complete]
```

The operations boundary now separates the completed O1A contract from production work:

```text
O1A pure replay-then-queue round / idle contract  [complete]
  -> O1B sealed-record discovery / one I1-GC delegation
  -> O1C B2 discovery / one O0-compatible C2 delegation
  -> O1D ordering / fairness / retry-time / backoff / jitter
  -> O1E stale recovery / cancellation / graceful shutdown
  -> O1F production validation
```

The remaining I1-G durability work is:

```text
I1-GD retention / orphan reconciliation / cleanup
  -> I1-GE full production crash validation
```

This section supersedes earlier roadmap entries that list I1-GC itself as pending.
I1-GC does not add discovery, batch replay, retry loops, cleanup, B3 transitions,
C2 execution, workers, M3 writes, or UI.
