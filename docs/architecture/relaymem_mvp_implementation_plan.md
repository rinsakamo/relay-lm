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

RelayMEM's immediate goal is no longer another persistence primitive. M3a-M3h, C1-1/C1-2 execution, C1-4 fault convergence, C1-5 protected-source restart recovery, C2 one-job execution, and Phase I-1 later-turn recall with character/namespace isolation now exist. The next product goal is real SOUL Lab observation and auditable correction while Secondary MEM remains deferred until Integration Milestone I1 closes.

## Core lifecycle

```text
Short-term CTX
  -> governed experience evidence
  -> Primary MEM / Experience MEM
  -> RelaySLP consolidation
  -> Secondary MEM / Crystallized MEM
  -> SOUL Lab observation and correction
```

The completed Primary loop is:

```text
ordinary turn
  -> autonomous safe Primary MEM formation
  -> durable page/index/log result
  -> later-turn retrieval and RelayCTX injection
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

MEM-M4 Secondary MEM consolidation: deferred until Integration Milestone I1 closes
MEM-M5 Lab-ready memory operations: observation next, mutation after observation
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

## Non-goals for the completed Primary loop

The Primary loop did not require:

- TTS or Live2D execution,
- vector database or embedding retrieval,
- Secondary MEM consolidation,
- automatic RelaySOUL mutation,
- per-turn user approval for ordinary safe memory,
- broad visible-response rewriting,
- frontend chat-history authority restoration,
- queue scanning, daemon scheduling, or a generalized worker pool.

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

Retrieval remains read-only, character/namespace scoped, and unable to mutate RelaySOUL.

## MEM-M3: Primary MEM formation and persistence

### M3a-M3d — complete

These slices provide governed input validation, kind/safety classification, RelaySCN policy consumption, bounded RelayEMO salience, lineage, memory-write idempotency, deterministic page construction, and exact writer handoff.

### M3e — complete

M3e publishes one exact selected Primary page behind explicit gates with no-clobber secure publication and immediate path/lineage/digest/page/idempotency revalidation.

### M3f — complete

M3f securely reopens page and control state and derives an exact ordered reconciliation plan without mutation.

### M3g — complete

M3g consumes one exact M3f plan and applies required index/log updates with index-before-log ordering, atomic replacement, durability checks, and retryable partial-progress classification.

### M3h — complete

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

C2 accepts one exact caller-selected queued record. It does not create a scanner, scheduler, daemon, retry sleeper, or worker pool.

## MEM-M3i-c: ordinary next-turn recall — complete

Phase I-1 completes the ordinary recall portion while reusing exact C1/M3/M2 artifacts rather than public projections.

Completed scope:

- verify new memory is discoverable by M2,
- prove correct character and namespace isolation,
- verify backend context contains only bounded selected memory,
- keep visible response delivery independent of deferred work,
- preserve duplicate-dispatch and worker-retry idempotency,
- validate canonical Primary page/index/log state before injection,
- distinguish C1-5 post-enqueue restart recovery from the unresolved pre-enqueue background-finalizer window.

Completed end-to-end smoke:

1. submitted a managed turn yielding one eligible governed experience,
2. verified durable source publication and B2 enqueue,
3. claimed and executed one job through C2,
4. verified M3e page and M3g index/log state,
5. confirmed M3h and B3 outcome,
6. submitted a later turn requiring that memory,
7. verified M2 selection and RelayCTX injection,
8. verified wrong-character and wrong-namespace isolation,
9. replayed/retried and verified both idempotency domains.

## MEM-M4: Secondary MEM consolidation — deferred

M4 will consolidate related Primary MEM into stable Secondary MEM using SOUL anchors, lineage, contradiction checks, duplicate/supersession handling, and retrieval needs.

Primary MEM formation and recall are now proven, but M4 remains deferred until Integration Milestone I1 closes its real observation, auditable correction, and accepted pre-enqueue durability boundary.

Expected later scope:

- group related Primary MEM,
- detect duplicate and superseded items,
- produce stable summaries, concepts, project states, relationship summaries, claims, and relations,
- preserve full lineage,
- hold unresolved contradiction,
- emit RelaySOUL proposal candidates without direct mutation,
- support idempotent and rollback-friendly apply.

## MEM-M5: Lab-ready memory operations — planned

Initial read surface:

```text
GET /lab/api/characters/{character_id}/memory/recent
GET /lab/api/characters/{character_id}/memory/held
GET /lab/api/characters/{character_id}/lab/last-run/memory/used
```

Initial mutation priority:

```text
POST /lab/api/characters/{character_id}/memory/{memory_id}/correct
```

Correction is first because it proves that explicit intervention changes later retrieval while preserving auditable prior state. Forget/hide, pin/unpin, merge, and held-candidate review/apply/discard follow later.

All operations must be scoped by character, namespace, and concrete run/session or memory identity. Browser state is never authoritative for durable memory.

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
- deferred failure does not invalidate visible response.

## Sequencing rule

With M3i next-turn recall and scope isolation complete, prefer SOUL Lab observation, auditable correction, and the explicit I1-G pre-enqueue durability contract over new persistence schemas, recovery layers, or Secondary MEM behavior. Additional recovery work requires concrete evidence that the existing M3h/C1-4 retry/manual/isolation boundary is insufficient.

## Phase I-1 integration status

Primary MEM next-turn recall and character/namespace isolation are complete. The implementation keeps M2 as discovery owner, validates durable M3 page/index/log state, deduplicates write identity, and injects only bounded summary evidence. Secondary MEM consolidation and Lab correction remain later.
