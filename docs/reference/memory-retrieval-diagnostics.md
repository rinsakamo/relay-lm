# MEMORY Retrieval Diagnostics

`select_memory_chunks_with_diagnostics(...)` is the explicit retrieval-stage diagnostics surface for the current bounded `MEMORY.md` heading selector.

The ordinary `select_memory_chunks(...)` API preserves its existing return type and selection behavior. Both public entry points delegate to the same private selection owner, so diagnostics do not create a second retrieval implementation or ranking authority.

## Current observations

The diagnostics object contains only aggregate mechanics from the retrieval attempt:

- `mode`;
- parsed heading-chunk count;
- positive lexical candidate count;
- selected count;
- explicit chunk-count limit;
- explicit character limit and used characters;
- positive candidates skipped because the remaining character budget could not fit the complete chunk;
- positive candidates left unadmitted after the chunk-count limit was already full;
- separate chunk-count and character-budget pressure booleans.

No heading path, Markdown location, chunk content, query term, lexical score, State value, or Event identifier is emitted.

## Reason attribution

Reason attribution follows the existing selector order without changing selection semantics:

1. positive lexical candidates are ranked exactly as before;
2. while a chunk slot remains, a candidate that cannot fit whole in the remaining character budget is counted as a character-budget skip and selection continues;
3. after the chunk-count limit is full, later positive candidates are counted as unadmitted by the chunk limit;
4. selected chunks are still restored to document order before return.

A zero chunk or character budget returns immediately without parsing `MEMORY.md`. Diagnostics therefore report zero observed candidates and no inferred pressure for work that was never performed. Missing memory and missing/empty query input likewise do not invent unseen candidate populations.

These counters describe retrieval mechanics only. They do not establish semantic authority, confidence, relevance quality, truth, telemetry requirements, or a default runtime budget.

## Deferred

Event-retrieval diagnostics, integrated ordinary-turn retrieval diagnostics, total cross-layer/token-aware cost, runtime default budgets, semantic/vector retrieval, and broader State-vs-memory conflict handling remain separate #1267 work.

The wider Context Compiler authority remains `docs/architecture/context-compiler.md`; that compiler still does not infer upstream MEMORY retrieval pressure when it receives already-selected chunks.