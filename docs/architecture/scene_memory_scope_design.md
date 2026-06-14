# Scene-aware Memory Scope Design

## Scope

This document defines how Scene metadata should influence RelayMEM candidate selection and memory namespace boundaries.

It is a docs-only design note. It does not introduce memory writes, retrieval implementation changes, or runtime behavior changes.

## Goal

RelayLM now has explicit boundaries for:

```text
scene_id
scene_state
session_id
room_id
character_id
user_id / user_type
memory_namespace
```

The next step is to clarify how these fields should influence memory candidate selection without confusing scene state, memory records, and runtime compile artifacts.

## Non-goals

This design does not add:

- memory database writes
- embedding or vector database implementation
- automatic scene detection
- automatic memory persistence from compiled prompts
- hard rejection when memory scope metadata is missing
- backend routing changes
- persona source mutation
- RelaySOUL artifact creation

## Core principle

RelayMEM proposes memory candidates. RelayCTX decides how selected candidates are packed into context.

```text
RelayMEM:
  memory sources, scopes, candidate retrieval, candidate metadata

RelaySCN:
  scene policy and allowed memory scope

RelayCTX:
  block assembly, token budget packing, prompt placement

Runtime Compile Gate:
  request-local decision phase for whether compiled context is applied

RelayRUN:
  runtime fallback/recovery orchestration and trace/checkpoint artifacts
```

Scene-aware memory scope should first be metadata for candidate filtering, ranking, and diagnostics. It should not become a write path until explicit memory write gates exist.

## Scope dimensions

### character_id

Identifies which persona is speaking.

Use for:

- character-specific memories
- character-specific stable summaries
- persona-specific retrieval scope

### user_id / user_type

Identifies the counterpart or class of counterpart.

Use for:

- durable relationship memory
- user-specific facts
- viewer/user preferences
- anonymous or public-group fallbacks

### scene_id

Identifies the current conversational situation or scenario.

Use for:

- scene-specific temporary memories
- topic/situation-specific retrieval bias
- separating roleplay/debugging/support modes
- scene transition diagnostics

### session_id

Identifies the runtime conversation/session run.

Use for:

- recent-session context
- temporary memory candidates
- diagnostics and trace correlation

Session is operational. Scene is semantic.

### room_id

Optional external host metadata.

Use for:

- frontend/channel/stream scoping
- group chat or room-level memory candidates
- diagnostics

`room_id` should not become prompt content by default.

### memory_namespace

Explicit configured memory namespace.

Use for:

- route-level memory partitioning
- character memory stores
- test/demo isolation
- future backend-specific memory sources

## Memory classes

Suggested memory classes:

```text
character_memory:
  durable memory associated with a character

relationship_memory:
  durable memory associated with a character/user pair

scene_memory:
  temporary or semi-durable memory associated with a scene_id

session_memory:
  short-lived memory associated with a session_id

room_memory:
  host-level or group-level memory scoped by room_id

retrieved_external_context:
  RAG/spill/source chunks that are not RelayLM memory records
```

These classes are roles, not necessarily separate physical stores.

## Candidate selection order

A conservative candidate selection order:

```text
1. required stable profile summaries
2. relationship/user memory candidates
3. scene-specific memory candidates
4. session-recent candidates
5. room/group candidates
6. external retrieved context
```

RelayCTX may reorder final prompt blocks by stability class. Candidate selection order is not the same as prompt placement.

## Prompt placement

Memory candidates should not automatically rewrite persona.

Preferred placement:

```text
stable_prefix
  common_runtime_policy
  SOUL.md
  OUTPUT_POLICY.md
  RELATIONSHIP_ANCHOR.md

slow_prefix
  STABLE_MEMORY_SUMMARY.md
  durable relationship memory summary

dynamic_suffix
  SCENE_STATE.md / scene_state
  selected scene memory
  selected session memory
  selected room/group memory
  retrieved external context
  recent turns
  latest input
```

Safety rule: dynamic or retrieved memory should usually appear after stable persona blocks.

## Candidate metadata

A memory candidate should carry metadata such as:

```yaml
candidate_id: mem_candidate_001
memory_class: scene_memory
memory_namespace: character/mili
character_id: mili
user_id: user_123
user_type: known_user
scene_id: stream_qna
session_id: session_001
room_id: openwebui_conversation_123
source_type: memory_record
recency_rank: 3
relevance_score: 0.82
scope_match:
  character: true
  user: true
  scene: true
  session: false
  room: false
selected_for_compile: true
selection_reason: scene_and_user_match
```

MVP implementations may only log a subset of these fields.

## Scope matching policy

Recommended matching behavior:

```text
exact character_id match:
  strong positive signal

exact user_id match:
  strong positive signal for relationship memory

scene_id match:
  positive signal for temporary or situation-specific memory

session_id match:
  strong recency signal, weak durability signal

room_id match:
  group/host signal, not identity signal

memory_namespace match:
  required or strong positive signal depending on route policy
```

Missing optional fields should degrade gracefully rather than block retrieval.

## Fallback behavior

If scene metadata is missing:

```text
scene_id missing:
  use default/null scene scope and avoid scene-specific hard filters

scene_state missing:
  compile without scene_state block

session_id missing:
  omit session-specific retrieval or use runtime request-local fallback

room_id missing:
  omit room-level candidates
```

Memory candidate selection should fail soft. Normal chat forwarding should remain available.

## Relationship to Scene Lifecycle

Scene Lifecycle defines how `scene_id`, `scene_state`, `session_id`, and `room_id` should be interpreted.

This document defines how those fields may influence memory candidate selection.

```text
Scene Lifecycle:
  what the metadata means

Scene-aware Memory Scope:
  how metadata scopes memory candidates
```

## Relationship to Runtime Compile Artifact Contract

Memory candidates are not compile artifacts by default.

```text
memory candidate:
  proposed source item from RelayMEM

CompilePlan:
  plan to include or omit selected candidates

CompileResult:
  rendered prompt blocks/messages

TraceEvent:
  compact RelayRUN runtime event about selection/decision
```

Compiled context should not become a memory record unless a future explicit memory write gate approves it.

## Relationship to RelaySOUL

RelaySOUL owns persona-source mutation workflows. Scene-aware memory candidate selection must not mutate SOUL, OUTPUT_POLICY, RELATIONSHIP_ANCHOR, STABLE_MEMORY_SUMMARY, or SCENE_STATE.

If future memory-derived summaries update persona or stable memory files, that should go through RelaySOUL-style approval, preflight, persistence, and rollback gates.

## Diagnostics

Suggested diagnostics fields:

```yaml
memory_scope_status: ok
memory_namespace: character/mili
character_id: mili
user_id_present: true
scene_id: stream_qna
session_id_present: true
room_id_present: true
candidate_count: 12
selected_candidate_count: 4
scope_fallback_reason: null
selected_memory_classes:
  - relationship_memory
  - scene_memory
  - session_memory
omitted_memory_classes:
  room_memory: no_room_match
```

Diagnostics should avoid storing full memory text unless explicitly needed for a developer-only dry run.

## Minimal MVP target

A minimal scene-aware memory scope should support:

1. explicit `memory_namespace` as the primary route-level boundary
2. optional `character_id` and user scope metadata in diagnostics
3. optional `scene_id` metadata for future candidate ranking
4. optional `session_id` metadata for recent-session scope
5. optional `room_id` metadata for host/group scope
6. no hard failure when optional scope fields are missing
7. no memory writes from compile or retrieval paths

## Future extensions

Future work can add:

- scene-aware retrieval ranking
- scene transition memory carryover rules
- temporary scene memory stores
- session-to-scene memory promotion gates
- room/group memory policies
- memory candidate risk scoring
- RelayRUN trace/checkpoint lineage and typed audit projections for memory candidate selection
- explicit memory write approval gates
