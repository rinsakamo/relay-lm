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
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - context_packing_design.md
---
# RelayMEM MVP Implementation Plan

## Purpose

This document defines the RelayMEM MVP implementation track. Repository-wide sequencing remains owned by [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

M3a-M3h, C1-1/C1-2 execution, C1-4 fault convergence, C1-5 protected-source restart recovery, C2 one-job execution, O0 explicit local one-job operation, Phase I-1 next-turn recall, Phase I-2 real Lab observation, and Phase I-3 Correct are complete. Phase I-4A defines the target Forget / Hide contract. The next RelayMEM governance implementation slice is I-4B, not production Forget completion.

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

Defined target loop, not implemented:

```text
current active Primary MEM
  -> read-only Forget preflight
  -> explicit token-gated apply
  -> immutable hidden successor revision
  -> index/log and M2 exclusion convergence
  -> immutable Forget tombstone
```

## Current implementation position

```text
MEM-M0 lifecycle and terminology: complete baseline; I-4A target lifecycle extension defined
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
  O0 explicit local one-job caller: complete as an operations boundary
  M3i-c next-turn recall and scope isolation: complete as Phase I-1
  M3i-d real read-only Lab observation: complete as Phase I-2
  M3i-e auditable Correct: complete as Phase I-3

MEM-M4 Secondary MEM consolidation: deferred
MEM-M5 Lab-ready memory operations:
  real observation reads: complete as Phase I-2
  auditable Correct: complete as Phase I-3
  Forget / Hide contract: defined target as Phase I-4A
  Forget resolver/apply/M2/UI/smoke: unimplemented as I-4B through I-4F
  Pin/Merge/Held review: later
```

## Independence and integration

```text
Phase 6 owns queue and worker control
RelayMEM owns memory meaning, lifecycle, and persistence
RelayCTX owns later-turn packing
SOUL Lab owns bounded observation and explicit operations through server APIs
```

RelayMEM may evolve independently from TTS, Live2D, and Runtime adapter delivery, but runtime wiring and retrieval convergence remain mandatory for completion claims.

## Non-goals for the current boundary

Phase I-4A does not require or implement:

- production Forget apply or M2 exclusion,
- SOUL Lab Forget UI,
- physical deletion, secure erase, purge, restore, or unhide,
- vector database or embedding retrieval,
- Secondary MEM consolidation,
- RelaySOUL mutation,
- broad memory administration,
- per-turn approval for ordinary safe memory,
- queue scanner, scheduler, daemon, or supervised worker lifecycle,
- TTS or Live2D execution.

## MEM-M1: store contract — complete

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

Phase I-2 observation data and Phase I-3 correction artifacts live outside M1/M2 candidate discovery. Future Forget prepared/tombstone artifacts must also remain runtime-private non-candidates.

## MEM-M2: retrieval usable foundation — complete

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

Phase I-3 adds current-revision resolution without adding a correction-specific retriever. I-4B/I-4D must replace the correction-only state view with one canonical Primary current-state resolver used by M2 and Lab reads.

Target eligibility:

```text
active + converged + valid scope/page/controls -> eligible for ordinary M2 ranking
hidden                                     -> excluded
prepared or recovery_required              -> excluded fail-closed
corrupt or ambiguous lifecycle chain       -> excluded fail-closed
prior physical revision                    -> excluded
```

No production hidden-state filtering exists yet.

## MEM-M3: Primary MEM formation and persistence — complete

M3a-M3d provide governed input validation, safety classification, RelaySCN policy use, bounded RelayEMO salience, lineage, memory-write idempotency, deterministic page construction, and exact writer handoff.

M3e publishes one exact selected Primary page with no-clobber secure publication and immediate revalidation. M3f/M3g derive and apply canonical index-before-log reconciliation. M3h audits exact receipt/store convergence read-only.

## MEM-M3i-a: worker integration contracts — complete

Completed integration includes exact worker-to-M3a evidence, outcome classification, dispatch/memory idempotency separation, lease-fenced one-claim execution, crash/lock/stale/corrupt convergence, and durable protected-source restart rehydration. These boundaries do not scan or schedule the queue.

## MEM-M3i-b: one-job runtime integration — complete

```text
finalized ordinary turn
  -> Phase 6 durable source + queue publication
  -> one-job adapter performs canonical B3 claim
  -> C1-5 rehydrates fresh C1-0 source
  -> C1-2 executes M3a-M3h and transitions B3
  -> verified durable Primary MEM
```

C2 owns one caller-selected queued record and adds no scanner, scheduler, worker pool, retry sleep, or daemon lifecycle. O0 is the completed explicit local caller that selects and delegates at most one eligible queued record without changing RelayMEM or C2 authority.

## MEM-M3i-c: next-turn recall and scope isolation — complete

Phase I-1 proves existing M2 discovers the new memory, exact character/namespace scope is required, only bounded selected memory reaches RelayCTX/backend context, wrong scopes cannot observe it, and duplicate dispatch/worker retry preserve distinct idempotency domains.

M3i-c next-turn recall and scope isolation: complete as Phase I-1.

## MEM-M3i-d: real Lab observation — complete

Phase I-2 provides loopback-only exact-schema APIs for latest completed run, recent validated Primary memories, held/blocked outcomes, and memories actually included in backend-bound context.

M3i-d real read-only Lab observation: complete as Phase I-2.

Observation receipts are read-model evidence only. They are not M1/M2 candidates, protected source, B3 records, lifecycle authority, or repair instructions. Observation receipt failure cannot change memory semantics or visible response behavior.

## MEM-M3i-e: auditable Correct — complete

Phase I-3 provides read-only correction preflight, bounded semantic diff, short-lived token, exact revision fence, immutable successor page, M3f/M3g convergence, immutable correction receipt, recovery, exact replay, and later M2 resolution of only the corrected current revision.

Past used-memory evidence preserves the representation actually injected for that run. Durable correction audit evidence remains distinct from observation receipts.

## MEM-M4: Secondary MEM consolidation — deferred

M4 will group related eligible active Primary MEM, detect duplicate/supersession/contradiction, produce stable summaries and relations, preserve lineage, hold unresolved conflicts, and emit RelaySOUL proposal candidates without direct SOUL mutation.

Canonical hidden Primary MEM is ineligible for ordinary consolidation unless a future explicit contract states otherwise.

## MEM-M5: Lab-ready memory operations

### Read surface — complete as Phase I-2

The read surface observes current runtime evidence. It does not create, replace, hide, pin, merge, apply, discard, or repair memory.

### First mutation — complete as Phase I-3

Correct is implemented through exact loopback preflight/apply/history routes and changes later retrieval through one immutable successor revision.

Required invariants remain exact current identity/scope, no browser path authority, bounded explicit input, no-clobber publication, preserved prior representation/provenance, durable audit evidence distinct from observation receipts, later M2 convergence, crash-safe recovery, and no RelaySOUL mutation.

### Forget / Hide contract — defined as Phase I-4A

Canonical terms:

```text
Forget            user-facing explicit operation
hidden            canonical current retrieval-ineligible lifecycle state
Forget tombstone  immutable runtime-private audit/recovery artifact
```

Persistence decision:

```text
revision N active
  -> immutable successor Primary page through M3e
revision N+1 hidden
  -> M3f/M3g index/log convergence
  -> retrieval exclusion verification
  -> immutable Forget tombstone
```

The page revision is lifecycle authority. A tombstone is not an independently mutable sidecar flag. Correct and Forget must share the same per-memory revision claim and pending-operation fence.

### I-4 implementation slices

```text
I-4B  canonical current-state resolver, shared fence, exact preflight/history/token
I-4C  hidden successor apply, prepared artifact, tombstone, exact replay
I-4D  index/log convergence, M2 exclusion, historical lifecycle projection
I-4E  loopback API and SOUL Lab Forget UI
I-4F  crash/race/security/fresh-conversation exclusion validation
```

All remain unimplemented.

## Safety invariants

All RelayMEM slices preserve source lineage, exact character/namespace isolation, bounded content, fail-closed corruption handling, separate idempotency domains, autonomous ordinary memory only when gates pass, explicit user action for destructive lifecycle operations, no authority inversion over Secondary/SOUL, no generic trace leakage, and no direct RelaySOUL mutation.

For Forget specifically:

- a hidden lifecycle commit never rolls back to active because audit/HTTP finalization failed,
- prepared/recovery/corrupt state never exposes memory to ordinary retrieval,
- exact replay creates no new revision or tombstone,
- historical used-memory receipts are never rewritten,
- Forget is not a legal-erasure or physical-deletion claim.

## Sequencing rule

With Correct complete and I-4A defined, I-4B is the next bounded RelayMEM governance implementation slice. It may narrow-refactor the correction-specific resolver and lock/fence into a shared Primary mutation coordinator, but must not perform a broad generic mutation-framework rewrite.

UI-B0 and O0 are complete. The next parallel work is I1-GB durable-finalization publication, I-4B canonical resolver/shared-fence/read-only contracts, and O1 scanner/retry-scheduler design under their existing ownership boundaries.

## Completion status

- Primary MEM formation/persistence: complete
- one-job Phase 6 execution: complete
- O0 explicit local one-job caller: complete
- next-turn retrieval and RelayCTX injection: complete
- character/namespace isolation: complete
- real SOUL Lab observation: complete
- auditable Correct: complete
- Phase I-4A Forget / Hide contract: defined target
- production Forget runtime, M2 exclusion, and UI: unimplemented
- Secondary MEM consolidation: deferred

## I1-G boundary

M3i-c next-turn recall and scope isolation: complete as Phase I-1.
M3i-d real read-only Lab observation: complete as Phase I-2.
I1-G pre-enqueue background-finalizer durability remains unresolved. Observation receipts cannot repair a turn that never reached durable protected-source and B2 queue publication. I1-GA defines the target and fault model only.
