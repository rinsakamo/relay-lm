---
relaylm_doc_type: implementation_plan
relaylm_authority: relaymem_mvp_independent_track
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - RelayMEM MVP slice lands
  - RelaySLP persistence sequencing changes
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
  - context_packing_design.md
---
# RelayMEM MVP Implementation Plan

## Purpose

This document defines the independent RelayMEM MVP implementation track.

RelayMEM MVP can progress independently from Phase 5.5 Stream Unpack, TTS adapter handoff, SOUL Lab UI, and SOUL Lab Runtime work as long as it keeps narrow integration points with RelayCTX, RelaySCN, RelayEMO, RelayRUN, and RelaySOUL.

Repository-wide implementation status and global sequencing remain owned by [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md). This document owns the RelayMEM-M bounded track shape.

## Core boundary

```text
RelayMEM-M track
  -> local memory store contracts
  -> read-only retrieval usability
  -> primary experience memory formation
  -> secondary crystallized memory consolidation
  -> Lab-ready memory operation APIs
```

The track must preserve the lifecycle defined in [Memory Lifecycle Design](memory_lifecycle_design.md):

```text
Short-term CTX
  -> governed experience evidence
  -> Primary MEM / Experience MEM
  -> RelaySLP consolidation
  -> Secondary MEM / Crystallized MEM
  -> SOUL Lab observation/correction
```

## Independence assumptions

RelayMEM MVP does not require:

- Phase 5.5 Stream Unpack completion,
- TTS segmentation or adapter handoff,
- TTS execution,
- Live2D/avatar control,
- SOUL Lab UI implementation,
- SOUL Lab Runtime implementation,
- vector database infrastructure,
- embedding retrieval,
- automatic RelaySOUL mutation.

It may use existing runtime foundations:

- RelayCTX Repack placement and payload mutation helpers,
- RelaySCN memory scope and persistence policy,
- RelayEMO salience evidence in bounded form,
- RelayRUN idempotency, checkpoint, and content-free operation projection patterns,
- RelayMEM read-only retrieval/store diagnostics already present in current implementation.

## Non-goals for the RelayMEM MVP track

RelayMEM MVP must not introduce:

- per-turn user approval for ordinary memory formation,
- raw trace persistence as memory,
- direct RelaySOUL mutation,
- broad semantic rewriting of visible responses,
- frontend chat-history authority restoration,
- direct TTS/avatar behavior,
- synchronous latency-critical full SLP consolidation,
- unbounded filesystem scanning or unbounded memory page reads.

## Slice MEM-M0: lifecycle and terminology docs — planned/partial

Goal: establish the target memory layer model before runtime changes.

Scope:

- define Short-term CTX,
- define Primary MEM / Experience MEM,
- define Secondary MEM / Crystallized MEM,
- define SOUL anchor boundary,
- define autonomous ordinary memory formation,
- align Lab as observation/correction rather than approval queue.

Completion criteria:

- `memory_lifecycle_design.md` exists and is linked,
- RelayMEM and RelaySLP docs reference autonomous ordinary memory formation,
- SOUL Lab UI docs use memory formation / correction terminology.

This slice is docs-only and does not claim runtime implementation.

## Slice MEM-M1: primary/secondary store contract

Goal: make the local file-backed memory store layout ready for primary and secondary MEM without enabling broad writes, while explicitly defining the migration from the current `memory/raw` plus flat `memory/mem/*` layout.

Scope:

- introduce explicit store contract for primary and secondary memory classes,
- define allowed paths and blocked paths,
- define page metadata fields for memory layer, scope, source lineage, confidence/stability band, salience band, safety scope, and idempotency key,
- define index/log expectations for primary and secondary MEM,
- update read-only diagnostics to recognize primary/secondary layout,
- preserve read-only compatibility with the current flat layout until the migration slice lands,
- keep all writes disabled or dry-run-only by default.

Target layout:

```text
memory/
  sources/
    conversations/
    communications/
    corrections/

  mem/
    primary/
      sessions/
      scenes/
      relationships/
      projects/
    secondary/
      projects/
      concepts/
      claims/
      summaries/
      relations/
    index.md
    log.md
```

Migration note:

```text
Current documented/current-runtime layout:
  memory/raw/
  memory/mem/projects/
  memory/mem/concepts/
  memory/mem/summaries/
  memory/mem/relations/
  memory/mem/index.md
  memory/mem/log.md

Target MEM-M1 layout:
  memory/sources/
  memory/mem/primary/
  memory/mem/secondary/
```

MEM-M1 must either support the current flat layout as a read-only compatibility source or migrate it explicitly under dry-run/apply gates before MEM-M2 treats the new layout as canonical for retrieval.

Required safety:

- no symlink traversal,
- no absolute or parent-relative path escape,
- bounded scans,
- bounded reads,
- UTF-8 validation,
- content-free store diagnostics by default.

Smoke coverage:

- valid target layout discovery,
- current flat layout compatibility discovery,
- missing layout fallback,
- symlink block,
- unsupported file block,
- malformed UTF-8 block,
- bounded scan behavior,
- content-free diagnostics.

## Slice MEM-M2: retrieval usable MVP

Goal: make existing formed memory useful for current answers through safe retrieval and gated RelayCTX packing.

Scope:

- read primary and secondary MEM pages from the local store,
- select bounded candidates by namespace, memory layer, scope metadata, and keyword/tag summary matching,
- extract bounded snippets only in runtime-private artifacts,
- expose content-free retrieval projections,
- support gated snippet runtime injection through RelayCTX Repack,
- keep default-off / dry-run-only gates unless explicitly configured.

Retrieval priority:

```text
1. Secondary MEM summaries for stable continuity
2. Relationship/user secondary MEM
3. Scene/session primary MEM
4. Project/concept secondary MEM
5. External retrieved context only when explicitly configured
```

Authority rule:

```text
SOUL / OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  > Secondary MEM
  > RelaySCN
  > Primary MEM
  > Short-term CTX
  > latest input
```

Required safety:

- retrieval must not write memory,
- retrieval must not mutate RelaySOUL,
- ambiguous references must remain RelayINT/RelaySCN gated,
- primary MEM must not override secondary MEM or SOUL,
- raw memory bodies/snippets must not enter default trace/audit.

Smoke coverage:

- secondary-only retrieval,
- primary-only retrieval,
- mixed priority retrieval,
- namespace mismatch omission,
- scene/recovery persistence block,
- runtime-private snippet extraction,
- content-free projection,
- gated RelayCTX injection default-off,
- gated RelayCTX injection apply path.

## Slice MEM-M3: autonomous primary MEM formation

Goal: turn governed experience evidence into Primary MEM / Experience MEM after a turn, session, or communication event without requiring per-turn user approval.

Scope:

- define a bounded governed experience input artifact,
- consume RelaySCN scene/persistence policy,
- consume RelayEMO salience evidence in bounded form,
- produce primary memory candidates,
- classify memory kind and safety scope,
- support `free_to_update`, `review_required`, `explicit_approval_required`, and `never_auto_promote`,
- apply only `free_to_update` candidates when explicit apply gates pass,
- emit content-free operation projections.

Primary MEM candidate examples:

- session episode,
- communication episode,
- relationship moment,
- recent project event,
- scene-bound memory,
- salient but unresolved experience.

Required safety:

- raw affect estimates must not become durable facts,
- recovery/formal-document/medical-safety scenes must block persistence unless explicitly allowed by policy,
- low-confidence personal inference must not auto-promote,
- source lineage must be present,
- idempotency key must prevent duplicate writes,
- failure must not affect visible response delivery.

Smoke coverage:

- dry-run candidate generation,
- free-to-update apply default-off,
- free-to-update apply when gates pass,
- review-required hold,
- explicit-approval proposal block,
- never-auto-promote block,
- EMO salience preserved as metadata not fact,
- RelaySCN persistence block,
- idempotent duplicate prevention,
- content-free projection.

## Slice MEM-M4: secondary MEM consolidation

Goal: consolidate Primary MEM into Secondary MEM / Crystallized MEM using SOUL, existing MEM, lineage, contradiction checks, and retrieval needs.

Scope:

- read primary MEM candidates/pages,
- group related primary memories,
- detect duplicates and superseded items,
- produce secondary summaries, concept updates, project states, relationship summaries, claims, or relation updates,
- preserve source lineage,
- mark primary MEM as retained, summarized, superseded, or still active,
- emit SOUL proposal candidates only when identity/value/relationship-anchor changes are implicated.

Required safety:

- SOUL is read as an anchor but not mutated,
- contradictions must be held unless resolved,
- sensitive or identity-level changes must become proposal/approval artifacts,
- secondary MEM must not erase primary lineage,
- apply must be idempotent and rollback-friendly.

Smoke coverage:

- primary-to-secondary summary creation,
- duplicate merge,
- supersede older primary memory,
- contradiction hold,
- SOUL proposal candidate generation without SOUL mutation,
- content-free projection,
- idempotent apply.

## Slice MEM-M5: Lab-ready memory operations API

Goal: provide backend APIs that SOUL Lab can use later without making Lab UI a prerequisite.

Scope:

- list recently formed memories,
- list held/blocked memories,
- list memories used in a concrete latest response/run,
- correct memory,
- forget/hide memory,
- pin/unpin memory,
- merge memories,
- review/correct/apply/discard held memory items,
- expose content-free operation status for UI.

API shape is target-only until implemented, but should be scoped explicitly by character/user/session/memory namespace. Used-memory reads must be scoped to a concrete UI session, communication session, run ID, or last-run identifier; a character-only used-memory route is ambiguous when multiple tabs or sessions share one character.

Suggested route families:

```text
GET  /lab/api/characters/{character_id}/memory/recent
GET  /lab/api/characters/{character_id}/memory/held
GET  /lab/api/ui-sessions/{ui_session_id}/lab/last-run/memory/used
POST /lab/api/characters/{character_id}/memory/{memory_id}/correct
POST /lab/api/characters/{character_id}/memory/{memory_id}/forget
POST /lab/api/characters/{character_id}/memory/{memory_id}/pin
POST /lab/api/characters/{character_id}/memory/{memory_id}/unpin
POST /lab/api/characters/{character_id}/memory/{memory_id}/merge
POST /lab/api/characters/{character_id}/memory/held/{held_memory_id}/review
POST /lab/api/characters/{character_id}/memory/held/{held_memory_id}/correct
POST /lab/api/characters/{character_id}/memory/held/{held_memory_id}/apply
POST /lab/api/characters/{character_id}/memory/held/{held_memory_id}/discard
```

`memory_id` refers to already-formed memory. `held_memory_id` refers to a held `review_required` item that is not yet a formed durable memory. `GET /lab/api/ui-sessions/{ui_session_id}/lab/last-run/memory/used` returns the memories used by the latest response within that concrete UI session.

Required safety:

- destructive forget/delete requires explicit user action,
- pin/unpin may require explicit action because it changes retrieval priority,
- held-memory apply must re-run persistence and namespace gates,
- correction preserves lineage,
- cross-namespace operations are blocked by default,
- browser never directly reads/writes raw MEM files.

Smoke coverage:

- scoped list operations,
- session-scoped used-memory list operation,
- correction dry-run/apply gate,
- forget dry-run/apply gate,
- pin/unpin operation,
- held-memory review/correct/apply/discard operation,
- merge operation,
- namespace mismatch block,
- content-free UI status projection.

## Recommended implementation order

```text
MEM-M1 store contract
  -> MEM-M2 retrieval usable MVP
  -> MEM-M3 autonomous primary MEM formation
  -> MEM-M4 secondary consolidation
  -> MEM-M5 Lab-ready memory operations API
```

MEM-M2 can deliver near-term product value by making existing memory influence answers safely. MEM-M3 makes the system feel like experience accumulates. MEM-M4 makes memory stable and SOUL-aligned. MEM-M5 prepares SOUL Lab without blocking core memory work.

## Relationship to Phase 6 RelaySLP

Phase 6 asynchronous RelaySLP remains the broader deferred persistence/runtime orchestration phase.

The MEM-M track can start before full Phase 6 completion if each slice remains bounded:

- no always-on background worker required for MEM-M1/M2,
- turn-end or explicit invocation is enough for MEM-M3 dry-run/apply gates,
- scheduled/background consolidation can remain later for MEM-M4,
- Lab UI can remain later while MEM-M5 exposes backend contracts.

## Completion target for MEM MVP

RelayMEM MVP is strong enough when:

1. existing secondary MEM can be retrieved and safely packed into current answers,
2. primary experience memories can be formed autonomously under gates,
3. primary memories can later consolidate into secondary memories,
4. trace/audit remains content-free by default,
5. SOUL is never directly mutated by MEM,
6. Lab can later observe, correct, forget, pin/unpin, review held items, and merge memory without becoming a per-turn approval queue.
