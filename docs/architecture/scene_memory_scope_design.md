# Scene-aware Memory Scope Design

## Status

This is a target design note. It does not introduce memory writes, retrieval ranking changes, or a new current artifact schema.

Current Retrieval behavior remains in [RelayMEM Retrieval Execution Design](relaymem_retrieval_execution_design.md). Current phase status remains in [Project Status](../PROJECT_STATUS.md).

## Current implemented boundary

Current runtime has partial namespace/scope information through route/config state, RelaySCN v0, Retrieval v0, and diagnostics. It does not implement the complete candidate schema, scene-aware ranking policy, scene/session/room memory stores, or v1 projection below.

## Ownership

```text
RelaySCN
  allowed memory scope and persistence policy

RelayMEM Retrieval
  read-only candidates and scope metadata

RelayCTX
  final inclusion, order, and token budget

RelayRUN
  runtime state and typed projections

RelaySLP
  future deferred memory writes
```

Scene-aware scope first constrains selection. It does not authorize persistence.

## Target scope dimensions

- `character_id`: character-specific profile/memory scope.
- `user_id` / `user_type`: relationship/user scope.
- `scene_id`: semantic situation scope.
- `session_id`: operational recency scope.
- `room_id`: optional host/channel/group scope.
- `memory_namespace`: explicit route-level isolation boundary.

External IDs are protected metadata and are not prompt text or default trace content.

## Target memory classes

```text
character_memory
relationship_memory
scene_memory
session_memory
room_memory
retrieved_external_context
```

These are semantic roles, not necessarily separate physical stores.

## Target selection policy

A conservative target order is:

1. required approved profile summaries,
2. relationship/user memory,
3. scene-specific candidates,
4. session-recent candidates,
5. room/group candidates,
6. external retrieved context.

Selection order is not prompt placement; RelayCTX may reorder by stability and authority.

## Target runtime-private candidate

The following is a target example, not a current wire schema:

```yaml
candidate_id: mem_candidate_001
memory_class: scene_memory
memory_namespace: character/mili
character_scope_present: true
user_scope_present: true
scene_scope_present: true
session_scope_present: true
source_type: memory_record
recency_rank: 3
relevance_score: 0.82
selected_for_compile: true
selection_reason_class: scene_and_user_match
```

Exact external IDs, namespace values, local paths, and memory content remain runtime-private/protected.

## Target matching behavior

- character scope: strong positive signal,
- user scope: strong relationship-memory signal,
- scene scope: situation-specific signal,
- session scope: strong recency but weak durability,
- room scope: host/group signal rather than identity,
- memory namespace: required or strong signal according to route policy.

Missing optional fields should degrade without broadening scope silently.

## Fallback behavior

When optional metadata is absent:

- omit that optional scope,
- avoid filters that cannot be evaluated,
- preserve ordinary forwarding when the request is not memory-dependent,
- never broaden into unrelated namespaces.

## Runtime-private versus content-free diagnostics

A protected developer surface may expose exact configured namespace or external ID values when explicitly enabled under a separate retention/access policy.

Default persisted trace must instead use classes, counts, and presence flags:

```yaml
memory_scope_projection:
  schema_version: relaymem.memory_scope_projection.v1
  namespace_present: true
  character_scope_present: true
  user_scope_present: true
  scene_scope_present: true
  session_scope_present: true
  room_scope_present: false
  candidate_count: 12
  selected_candidate_count: 4
  selected_memory_classes:
    - relationship_memory
    - scene_memory
  fallback_reason_id: none
  content_free: true
```

This is a target projection until an implemented producer adopts it.

Default projections must not contain raw namespace values, character/user/room IDs, memory text, page paths, retrieval query terms, semantic scene content, or arbitrary nested candidates.

## Relationship to compile and persistence

A memory candidate is RelayMEM evidence. A compile plan/result is RelayCTX/runtime state. A trace event is a content-free RelayRUN projection.

Compiled context does not become a memory record. Retrieval does not create a persistence side effect. Future writes belong to RelaySLP and explicit gates.

## Required migration

Update together:

1. candidate schema and namespace validation,
2. scene-aware filtering/ranking,
3. runtime-private Retrieval result,
4. typed content-free projection code,
5. RelayCTX consumer metadata,
6. protected diagnostics policy,
7. scope, namespace, and trace smoke tests.
