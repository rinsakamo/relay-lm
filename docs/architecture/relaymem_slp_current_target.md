# RelayMEM / RelaySLP Current / Target Boundary

## Current implemented

Current RelayMEM provides `relaymem_retrieval.v0`, bounded candidate/snippet planning, selected gated context-injection helpers, typed content-free trace projection, and read-only durable-memory behavior.

Current implementation does not provide a complete asynchronous RelaySLP worker, scheduled/background execution, or page/index/log apply.

## Current compatibility

- Retrieval still consumes a historical RelayREF-shaped input from the RelayINT-facing wrapper.
- Current query preparation may use request messages.
- `relaymem.retrieval_runtime.v1`, `relaymem.retrieval_projection.v1`, and `relaymem.slp_projection.v1` do not have current producers.

## Target architecture

The detailed RelayMEM and RelaySLP documents define the target local-first store, typed relations, lint, safety scopes, deferred candidate compiler, and gated page/index/log updates. Those details remain target design rather than current runtime claims.

[Memory Lifecycle Design](memory_lifecycle_design.md) owns the target semantic boundary between RelayCTX short-term memory, governed experience evidence, autonomous ordinary MEM formation, and SOUL Lab observation/correction operations.

Ordinary MEM formation is target-autonomous by default. User approval is not the normal path for every memory candidate; review and approval are exception paths for sensitive, destructive, identity-level, low-confidence, contradictory, cross-namespace, or SOUL-affecting changes.

## Required migration

Update the typed RelayINT handoff, canonicalized query evidence, Retrieval result/projection split, RelayCTX consumers, deferred orchestration, storage/idempotency gates, RelaySOUL proposal handoff, SOUL Lab memory-operation UI, and smoke coverage together.

See [Memory Lifecycle Design](memory_lifecycle_design.md), [RelayMEM MVP Design](relaymem_mvp_design.md), [RelayMEM Retrieval Execution Design](relaymem_retrieval_execution_design.md), and [RelayMEM SLP Execution Design](relaymem_slp_execution_design.md).
