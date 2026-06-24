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
  - memory_lifecycle_design.md
  - relaymem_mvp_design.md
  - relaymem_slp_execution_design.md
  - relaymem_slp_current_target.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - relaymem_m3a_primary_formation_handoff.md
  - relaymem_m3d_primary_writer_handoff.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - context_packing_design.md
---
# RelayMEM MVP Implementation Plan

## Purpose

This document defines the RelayMEM MVP implementation track. Repository-wide sequencing remains owned by [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

RelayMEM's immediate goal is no longer another persistence primitive or another read-only adapter. M3a-M3h, C1-1/C1-2 execution, C1-4 fault convergence, C1-5 protected-source restart recovery, C2 one-job execution, Phase I-1 next-turn recall, and Phase I-2 real Lab observation are complete. The next goal is one auditable Correct operation whose effect is visible in later retrieval.

## Core lifecycle

```text
Short-term CTX
  -> governed experience evidence
  -> Primary MEM / Experience MEM
  -> RelaySLP consolidation
  -> Secondary MEM / Crystallized MEM
  -> SOUL Lab observation and explicit correction
```

The completed Primary loop is:

```text
ordinary turn
  -> autonomous safe Primary MEM formation
  -> durable page/index/log result
  -> later-turn retrieval and RelayCTX injection
  -> bounded read-only Lab observation
```

The next bounded loop is:

```text
observed Primary MEM
  -> explicit Correct request
  -> authoritative validated update
  -> durable audit evidence
  -> later M2 retrieval sees corrected representation
```

## Current implementation position

```text
MEM-M0 lifecycle and terminology: complete
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
  M3i-c next-turn recall and scope isolation: complete as Phase I-1
  M3i-d real read-only Lab observation: complete as Phase I-2

MEM-M4 Secondary MEM consolidation: deferred
MEM-M5 Lab-ready memory operations:
  real observation reads: complete as Phase I-2
  auditable Correct: next as Phase I-3
  forget/pin/merge/held review: later
```

## Independence and integration

RelayMEM may evolve independently from TTS, Live2D, and SOUL Lab Runtime. It must not remain disconnected from Phase 6 runtime orchestration.

```text
Phase 6 owns queue and worker control
RelayMEM owns memory meaning and persistence
RelayCTX owns later-turn packing
SOUL Lab owns observation and explicit operations through server APIs
```

Track independence permits parallel work; it does not make runtime wiring optional.

## Non-goals for the current memory-operation boundary

The current milestone does not require:

- TTS or Live2D execution,
- vector database or embedding retrieval,
- Secondary MEM consolidation,
- automatic RelaySOUL mutation,
- broad memory administration,
- per-turn user approval for ordinary safe memory,
- frontend chat-history authority restoration,
- queue scanning, scheduler, or daemon lifecycle.

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

Phase I-2 adds a separate observation directory below the already resolved character partition. It is not a memory layer, is not indexed by M1/M2, and cannot repair Primary state.

## MEM-M2: retrieval usable foundation — complete

M2 supports bounded candidate selection by namespace, layer, scope metadata, and summary/tag matching; runtime-private snippet extraction; content-free projection; and gated RelayCTX injection.

Priority remains:

```text
1. Secondary MEM stable summaries
2. relationship/user Secondary MEM
3. scene/session Primary MEM
4. project/concept Secondary MEM
5. external retrieved context when explicitly configured
```

Authority remains:

```text
SOUL / OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  > Secondary MEM
  > RelaySCN
  > Primary MEM
  > Short-term CTX
  > latest input
```

Retrieval remains read-only, character/namespace scoped, and unable to mutate RelaySOUL. Phase I-2 observes the result; it does not become retrieval authority.

## MEM-M3: Primary MEM formation and persistence — complete

### M3a-M3d

These slices provide governed input validation, kind/safety classification, RelaySCN policy consumption, bounded RelayEMO salience, lineage, memory-write idempotency, deterministic page construction, and exact writer handoff.

### M3e

M3e publishes one exact selected Primary page behind explicit gates with no-clobber secure publication and immediate path/lineage/digest/page/idempotency revalidation.

### M3f-M3g

M3f securely reopens page and control state and derives an exact ordered reconciliation plan without mutation. M3g applies required index/log updates with index-before-log ordering, atomic replacement, durability checks, and retryable partial-progress classification.

### M3h

M3h consumes one exact M3g receipt, revalidates page/index/log read-only, and classifies no recovery, retry reconciliation, manual confirmation, or future journal-aware isolation. It does not repair.

## MEM-M3i-a: worker integration contracts — complete

Completed integration includes:

- exact worker-to-M3a evidence through C1-0/C1-1,
- held/blocked/retry/terminal mapping through C1-3,
- dispatch and memory-write idempotency separation through C1-2,
- lease-fenced one-claimed execution with bounded retry timing,
- crash, lock, stale-claim, corruption, and leakage convergence through C1-4,
- durable protected-source restart rehydration through C1-5.

These boundaries do not scan or schedule the queue.

## MEM-M3i-b: one-job runtime integration — complete

```text
finalized ordinary turn
  -> Phase 6 durable source + queue publication
  -> one-job adapter performs canonical B3 claim
  -> C1-5 rehydrates fresh C1-0 source
  -> C1-2 executes M3a-M3h and transitions B3
  -> verified durable Primary MEM
```

C2 owns exactly one caller-selected queued record. It does not add scanning, scheduling, worker pools, retry sleeping, or daemon lifecycle.

## MEM-M3i-c: next-turn recall and scope isolation — complete

Phase I-1 reuses exact C1/M3/M2 artifacts rather than public projections and proves:

- the new memory is discoverable by existing M2,
- the correct character and namespace are required,
- backend context contains only bounded selected memory,
- wrong-character and wrong-namespace requests cannot observe it,
- visible response delivery remains independent of deferred work,
- duplicate dispatch and worker retry preserve both idempotency domains,
- C1-5 post-enqueue restart recovery remains distinct from the unresolved pre-enqueue background-task window.

## MEM-M3i-d: real Lab observation — complete

Phase I-2 observes the completed runtime loop through exact read-only APIs:

```text
GET /lab/api/characters/{character_id}/lab/last-run?namespace=...
GET /lab/api/characters/{character_id}/memory/recent?namespace=...&limit=...
GET /lab/api/characters/{character_id}/memory/held?namespace=...&limit=...
GET /lab/api/characters/{character_id}/lab/last-run/memory/used?namespace=...
```

Properties:

- latest run uses completed-run evidence and deterministic canonical ordering, not filesystem mtime,
- recent memory reuses validated Primary page/index/log state,
- held and blocked remain distinct from formed retrievable memory,
- used-memory evidence distinguishes retrieval, candidate, selection, RelayCTX injection, backend-bound inclusion, and response completion,
- current representation remains separate from what was injected for that run,
- every API is character/namespace scoped, bounded, exact-schema, no-store, and loopback-only,
- observation receipt failure cannot change memory semantics or visible response behavior,
- raw prompt, transcript, protected source, path, digest, queue/lease state, and full pages are not exposed.

## MEM-M4: Secondary MEM consolidation — deferred

M4 will consolidate related Primary MEM into stable Secondary MEM using SOUL anchors, lineage, contradiction checks, duplicate/supersession handling, and retrieval needs.

M4 remains deferred until the Primary observation/correction loop is proven. Expected later scope:

- group related Primary MEM,
- detect duplicate and superseded items,
- produce stable summaries, concepts, project states, relationship summaries, claims, and relations,
- preserve full lineage,
- hold unresolved contradiction,
- emit RelaySOUL proposal candidates without direct mutation,
- support idempotent and rollback-friendly apply.

## MEM-M5: Lab-ready memory operations

### Read surface — complete as Phase I-2

The read surface is observe-only. It does not create, replace, hide, pin, merge, apply, discard, or repair memory.

### First mutation — next as Phase I-3

```text
POST /lab/api/characters/{character_id}/memory/{memory_id}/correct
```

The final route and schema must follow existing naming and ownership. Correction is first because it proves that explicit intervention changes later retrieval while preserving auditable prior state.

Required invariants:

- exact current memory identity, character, namespace, and validated store state,
- no browser-owned filesystem or authority mapping,
- bounded correction input and explicit user action,
- atomic/no-clobber authoritative update,
- preserved prior representation and provenance,
- durable audit evidence distinct from observation receipts,
- later M2 retrieval verifies the corrected representation,
- failure cannot partially corrupt page/index/log state,
- no RelaySOUL mutation.

Later operations include forget/hide, pin/unpin, merge, and held-candidate review/apply/discard.

## Safety invariants

All RelayMEM slices preserve:

- source lineage for durable facts,
- raw affect estimates do not become facts,
- low-confidence personal inference does not auto-promote,
- safety/recovery/formal-document policy may block persistence,
- ordinary `free_to_update` memory may apply only when gates pass,
- review/approval items remain held,
- destructive user operations require explicit action,
- Primary MEM cannot override Secondary MEM or SOUL authority,
- generic trace and public diagnostics remain content-free,
- no RelayMEM slice directly mutates RelaySOUL,
- deferred or observation failure does not invalidate visible response.

## Sequencing rule

With next-turn recall, scope isolation, and real observation complete, prefer one auditable Correct operation over new persistence schemas, recovery layers, Secondary MEM behavior, or broad UI actions. Additional recovery work requires concrete M3h evidence that the existing retry/manual/isolation boundary is insufficient.

## Completion status

- Primary MEM formation/persistence: complete
- one-job Phase 6 execution: complete
- next-turn retrieval and RelayCTX injection: complete
- character/namespace isolation: complete
- real SOUL Lab observation: complete
- auditable Correct: next
- Secondary MEM consolidation: deferred

## I1-G boundary after Phase I-2

M3i-c next-turn recall and scope isolation: complete as Phase I-1.
M3i-d real read-only Lab observation: complete as Phase I-2.
I1-G pre-enqueue background-finalizer durability remains unresolved. Observation receipts cannot repair it.

<!-- phase-i3-auditable-primary-mem-correct -->
## Phase I-3 auditable Primary MEM Correct — complete (2026-06-24)

Phase I-3 completes the first real observe/correct/retrieve loop. A formed Primary MEM observed through Phase I-2 can be corrected through read-only preflight, bounded semantic diff, explicit short-lived-token apply, immutable successor-page publication through the existing M3e boundary, canonical M3f/M3g index/log convergence, and immutable audit receipt finalization. Existing M2 retrieval resolves only the corrected current revision and existing RelayCTX injection remains the sole prompt path.

Character/namespace isolation, stable logical memory identity, no-clobber publication, exact operation idempotency, one-winner revision fencing, crash recovery, and historical used-memory integrity are preserved. Correction reason, audit receipt, paths, digests, lineage, queue/lease state, and prior full pages are not retrieval inputs or public prompt content.

Authority and exact contracts: `docs/architecture/phase_i3_auditable_primary_mem_correct.md`.

Still separate and unresolved: the I1-G process-exit window after visible-response delivery but before background-finalizer protected-source and B2 queue publication. Phase I-3 does not implement forget, pin/unpin, merge, held apply/discard, Secondary MEM consolidation, RelaySOUL mutation, queue scanner/scheduler/daemon, static UI serving, or TTS/audio/avatar execution.

