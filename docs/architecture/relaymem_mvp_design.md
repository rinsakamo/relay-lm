# RelayMEM MVP Design

## Purpose

RelayMEM is RelayLM's long-term memory boundary. This document separates the current Retrieval/runtime-injection foundations from the target compiled-memory and RelaySLP architecture.

Current phase status remains in [Project Status](../PROJECT_STATUS.md) and [Pipeline Implementation Plan](pipeline_implementation_plan.md).

## Current implemented boundary

Current RelayMEM includes:

- `relaymem_retrieval.v0` dry-run/diagnostics-oriented retrieval,
- file-store diagnostics and bounded candidate/snippet planning,
- gated RelayMEM snippet and runtime-CTX injection helpers,
- typed content-free trace projection,
- read-only behavior for durable memory.

Current Retrieval still consumes a historical RelayREF-shaped compatibility input from the RelayINT-facing wrapper and may derive query terms from the current request messages.

Current implementation does not provide:

- a complete compiled `memory/mem/` page/index/log store,
- an asynchronous RelaySLP worker,
- page/index/log persistence apply,
- a typed `relayint.intent.v1` handoff,
- producer-owned `relaymem.retrieval_runtime.v1` and `relaymem.retrieval_projection.v1` artifacts.

## Stable ownership

```text
RelayMEM storage/index
  approved durable memory substrate

RelayMEM Retrieval
  synchronous read-only evidence for the current answer

RelaySLP
  deferred candidate compilation and future gated writes
```

Retrieval improves the current answer. RelaySLP improves future memory.

RelaySCN owns memory-scope and persistence policy. RelayINT decides whether retrieval is needed and whether reference scope is confirmed. RelayCTX owns final prompt inclusion and token-budget degradation. RelaySOUL owns durable persona revision rather than memory storage.

## Target storage model

The following is target architecture, not a claim that every directory or writer exists now:

```text
memory/
  raw/
    conversations/
    docs/
    events/
  mem/
    index.md
    log.md
    projects/
    concepts/
    claims/
    summaries/
    relations/graph.json
```

Target `raw_sources` preserve governed evidence separately from compiled pages. Target `mem_pages` contain approved project, concept, claim, preference, summary, and relation material. Target `mem_index` supports bounded retrieval. Target `mem_log` records governed memory operations and is distinct from generic runtime trace.

## Target safety scopes

- `free_to_update`: eligible only through an enabled, policy-allowed, lineage-aware, idempotent SLP apply gate.
- `review_required`: held for review.
- `explicit_approval_required`: routed to an approval/proposal artifact.
- `never_auto_promote`: rejected or kept only as protected source evidence.

Raw affect estimates, transient emotional interpretation, sensitive inference, and low-confidence personal inference are never durable facts by default.

## Retrieval path

```text
RelaySCN scope
  + RelayINT retrieval decision / confirmed reference scope
  -> approved candidate search
  -> safety and authority filter
  -> bounded runtime-private evidence
  -> RelayCTX final packing
```

Retrieval must not write memory, mutate RelaySOUL, silently resolve ambiguous references, broaden scope after a miss, or expose snippets/paths through default trace.

## Target RelaySLP path

```text
governed source evidence
  -> candidate extraction
  -> memory-kind and safety classification
  -> existing-page lookup
  -> merge / update / hold / reject
  -> relation typing and lint
  -> gated page/index/log update
  -> optional RelaySOUL proposal candidate
```

This is target behavior. The complete asynchronous apply path is not current implementation.

## Content boundary

Runtime-private memory artifacts may contain query text, candidate summaries/snippets, page/source references, proposed updates, and relation values.

Default persisted projections may contain only typed counts, source/scope classes, confidence bands, budgets, reason IDs, and apply booleans. They must not include raw messages, memory bodies, snippets, local paths, semantic scene/intent text, or final responses.

## Persistence rules

1. Retrieval only reads.
2. Target writes belong to RelaySLP and explicit persistence gates.
3. RelaySCN may block persistence regardless of candidate class.
4. review/approval-required candidates are held.
5. RelayMEM never directly mutates RelaySOUL.
6. raw evidence remains separate from compiled pages.
7. apply paths must be lineage-aware and idempotent.

## Required migration

Update together:

1. typed RelayINT-to-Retrieval handoff,
2. canonicalized current-turn query evidence,
3. runtime-private Retrieval result and typed projection split,
4. RelayCTX/runtime-injection consumers,
5. deferred RelaySLP worker/orchestration,
6. memory storage writer, index/log, revision and idempotency gates,
7. RelaySOUL proposal handoff,
8. Retrieval, SLP, storage, trace, and integration smoke tests.
