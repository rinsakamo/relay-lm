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
  - global Phase 5.5 Stream Unpack sequencing
  - exact RelayMEM runtime schema details
  - RelaySOUL approval contract details
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_implementation_plan.md
  - memory_lifecycle_design.md
  - relaymem_mvp_design.md
  - relaymem_slp_execution_design.md
  - relaymem_slp_current_target.md
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

RelayMEM's immediate goal is no longer to add another isolated persistence primitive. M3a-M3h already cover the bounded Primary MEM formation, publication, reconciliation, and recovery-audit chain. The next goal is to connect that chain to the ordinary deferred runtime and prove later-turn recall.

## Core lifecycle

```text
Short-term CTX
  -> governed experience evidence
  -> Primary MEM / Experience MEM
  -> RelaySLP consolidation
  -> Secondary MEM / Crystallized MEM
  -> SOUL Lab observation and correction
```

The active milestone focuses on the first usable loop:

```text
ordinary turn
  -> autonomous safe Primary MEM formation
  -> durable page/index/log result
  -> later-turn retrieval and RelayCTX injection
```

## Current implementation position

```text
MEM-M0 lifecycle and terminology: complete
MEM-M1 bounded store-layout compatibility/read-only diagnostics: complete
MEM-M2 bounded retrieval priority/snippet/injection foundations: complete

MEM-M3 Primary MEM path:
  M3a formation candidate: complete
  M3b source lineage and write preflight: complete
  M3c deterministic page candidate: complete
  M3d writer-handoff preflight: complete
  M3e atomic Primary page writer: complete
  M3f index/log reconciliation preflight: complete
  M3g index/log reconciliation apply: complete
  M3h read-only reconciliation recovery audit: complete
  M3i ordinary-runtime worker integration and next-turn recall: next

MEM-M4 Secondary MEM consolidation: planned after M3i
MEM-M5 Lab-ready memory operations API: planned after the real observation bridge begins
```

M3a-M3h are direct/helper boundaries. They do not prove that an ordinary finalized turn forms memory automatically, that a worker reaches them, or that the next turn retrieves the result.

## Independence and integration

RelayMEM may continue to evolve independently from TTS, Live2D, and SOUL Lab Runtime work. It must not remain independent from Phase 6 worker execution indefinitely.

The current integration contract is:

```text
Phase 6 owns queue and worker control
RelayMEM owns memory meaning and persistence
RelayCTX owns later-turn packing
SOUL Lab owns observation and explicit user operations through server APIs
```

Track independence permits parallel implementation. It does not make request-runtime and worker wiring optional.

## Non-goals for the active milestone

The active Primary MEM loop does not require:

- TTS execution,
- Live2D/avatar control,
- vector database infrastructure,
- embedding retrieval,
- Secondary MEM consolidation,
- automatic RelaySOUL mutation,
- per-turn user approval for ordinary safe memory formation,
- broad semantic rewriting of visible responses,
- frontend chat-history authority restoration.

## MEM-M1: store contract — complete

The local file-backed memory store recognizes Primary and Secondary memory classes, bounded allowed paths, layer/scope/source-lineage metadata, index/log control files, current-layout compatibility, secure path traversal rules, bounded scans/reads, UTF-8 validation, and content-free diagnostics.

Target layout remains:

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

M2 supports bounded candidate selection by namespace, layer, scope metadata, and summary/tag matching; runtime-private snippet extraction; content-free retrieval projection; and gated RelayCTX injection.

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

Retrieval must remain read-only, character/namespace scoped, and unable to mutate RelaySOUL.

## MEM-M3: Primary MEM formation and persistence

### M3a-M3d: candidate and handoff — complete

These slices provide:

- governed experience input validation,
- memory kind and safety-scope classification,
- RelaySCN persistence-policy consumption,
- bounded RelayEMO salience metadata,
- source lineage,
- memory-write idempotency,
- deterministic page construction,
- exact writer/store-target handoff.

### M3e: atomic page publication — complete

M3e may publish one exact selected Primary MEM page behind explicit default-off, dry-run-first gates. It uses no-clobber secure publication and revalidates path, lineage, digest, page shape, and memory-write identity immediately before write.

### M3f: reconciliation preflight — complete

M3f securely reopens the published page and bounded index/log state, then derives an exact ordered reconciliation plan without mutation.

### M3g: reconciliation apply — complete

M3g consumes one exact M3f plan and applies required index/log updates with index-before-log ordering, atomic replace, durability checks, and retryable partial-progress classification.

### M3h: recovery audit — complete

M3h consumes one exact M3g receipt, revalidates the current page/index/log store read-only, and classifies no-recovery, retryable reconciliation, manual confirmation, or future journal-aware recovery candidacy. M3h does not repair the store.

## MEM-M3i: ordinary-runtime integration and recall — next

### Goal

Turn the complete M3a-M3h primitive chain into a real deferred Primary MEM feature.

### Producer/consumer path

```text
finalized ordinary turn
  -> Phase 6 durable queue
  -> Phase 6 worker claims job
  -> M3a-M3h execute in order
  -> verified durable Primary MEM
  -> later RelayMEM retrieval
  -> RelayCTX injection
  -> later answer uses the memory
```

### Scope

M3i must:

- define the exact worker-to-M3a governed evidence handoff,
- reuse existing M3a-M3h artifacts rather than reconstructing them from public projections,
- map held/blocked/retryable/terminal RelayMEM outcomes to Phase 6 queue state,
- preserve dispatch idempotency separately from memory-write idempotency,
- expose only content-free operation status outside protected runtime domains,
- verify that newly written memory is discoverable by the current M2 retrieval path,
- prove correct character and namespace isolation,
- keep visible response delivery independent of deferred work.

### Required end-to-end smoke

1. submit a managed turn that yields one eligible governed experience,
2. verify deferred durable enqueue,
3. claim and execute one worker job,
4. verify M3e page publication and M3g index/log state,
5. run M3h and confirm the expected store classification,
6. submit a later turn requiring that memory,
7. verify M2 selects it and RelayCTX injects it,
8. verify wrong-character and wrong-namespace requests do not select it,
9. retry the same dispatch and verify queue and memory-write deduplication.

### Completion rule

M3 is not end-to-end complete until M3i passes. M3a-M3h completion means the persistence primitives exist; it does not mean the product memory loop is active.

## MEM-M4: Secondary MEM consolidation — deferred until M3i

M4 will consolidate related Primary MEM into stable Secondary MEM using existing SOUL anchors, lineage, contradiction checks, duplicate/supersession handling, and retrieval needs.

M4 remains important but must not precede proof that Primary MEM can be formed and recalled in the ordinary runtime.

Expected later scope:

- group related Primary MEM,
- detect duplicate and superseded items,
- produce stable summaries, concepts, project states, relationship summaries, claims, and relations,
- preserve full lineage,
- hold unresolved contradiction,
- emit RelaySOUL proposal candidates without direct SOUL mutation,
- support idempotent and rollback-friendly apply.

## MEM-M5: Lab-ready memory operations API — planned

M5 exposes server-owned APIs for real SOUL Lab observation and explicit memory operations.

Initial read surface:

```text
GET /lab/api/characters/{character_id}/memory/recent
GET /lab/api/characters/{character_id}/memory/held
GET /lab/api/ui-sessions/{ui_session_id}/lab/last-run/memory/used
```

Initial mutation priority:

```text
POST /lab/api/characters/{character_id}/memory/{memory_id}/correct
```

Correction is first because it provides the clearest proof that user intervention changes later retrieval behavior while preserving an auditable prior state.

Later operations:

- forget/hide,
- pin/unpin,
- merge,
- review/correct/apply/discard held candidates.

All operations must be explicitly scoped by character, namespace, and a concrete run/session or memory identifier. Browser state is never authoritative for durable memory.

## Safety invariants

All RelayMEM slices preserve:

- source lineage is required for durable facts,
- raw affect estimates do not become facts,
- low-confidence personal inference does not auto-promote,
- recovery/formal-document/medical-safety policy can block persistence,
- ordinary `free_to_update` memory may apply autonomously when gates pass,
- review-required and approval-required items remain held,
- destructive user operations require explicit action,
- Primary MEM cannot override Secondary MEM or SOUL authority,
- generic trace and public diagnostics remain content-free,
- no RelayMEM slice directly mutates RelaySOUL,
- failure does not invalidate an already valid visible response.

## Sequencing rule

Until M3i closes, prefer integration work that connects an existing RelayMEM producer or consumer over new persistence schemas, new recovery layers, or Secondary MEM behavior. Additional M3 recovery work requires concrete evidence from M3h that the existing retry/manual-confirmation boundary is insufficient.
