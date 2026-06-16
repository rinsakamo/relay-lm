# Scene-aware Memory Scope Current / Target Boundary

## Current implemented

Current runtime has partial namespace and scope metadata through route/config state, RelaySCN v0, Retrieval v0, and diagnostics.

It does not implement the complete candidate schema, scene-aware ranking policy, scene/session/room memory stores, or a `relaymem.memory_scope_projection.v1` producer.

## Target architecture

The detailed design describes character, user, scene, session, room, and memory-namespace dimensions for candidate filtering/ranking. These dimensions do not authorize writes; future writes remain RelaySLP-gated.

## Diagnostic boundary

Exact namespace values, external IDs, local paths, query text, and memory content belong to a protected runtime/developer surface.

Default persisted projections expose only scope presence flags, counts, enum classes, reason IDs, and `content_free=true`. They must not expose raw external IDs, namespace strings, paths, snippets, query terms, or semantic scene text.

## Required migration

Update candidate schema, namespace validation, filtering/ranking, runtime-private Retrieval results, typed projection code, RelayCTX consumers, and scope/trace smoke tests together.

See [Scene-aware Memory Scope Design](scene_memory_scope_design.md) and [RelayMEM Retrieval Execution Design](relaymem_retrieval_execution_design.md).
