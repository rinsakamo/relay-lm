# Integration I1: Primary MEM Two-Turn Recall

## Status

Implemented in Phase I-1.

```text
Turn 1 ordinary managed response
  -> I1-B durable source and B2 enqueue
  -> explicit one-record C2 claim / rehydrate / execute seam
  -> C1-2 and M3a-M3h
  -> terminal B3 success

Turn 2 ordinary managed request
  -> character-partitioned configured RelayMEM root
  -> existing M2 candidate discovery
  -> exact Primary page / index / log / namespace validation
  -> bounded request-local selected-memory artifact
  -> existing RelayCTX snippet injection
  -> backend-bound request
```

## Production ownership

The Phase does not add a queue scanner, scheduler, daemon, or a parallel
retriever. Existing M2 discovery remains the candidate owner. The new
`relaymem_primary_recall` adapter only narrows candidates already selected by
M2 and rebuilds the existing RelayCTX snippet handoff from validated bounded
Primary summaries.

Character isolation is represented by an opaque partition below the configured
RelayMEM root. Both the explicit C2 caller and the ordinary request path use
`resolve_relaymem_character_store_root()`. Namespace isolation remains an exact
property of the canonical Primary page and its matching index/log entries.
Session and run identifiers are not introduced as new long-term retrieval
restrictions.

## Validation and fail-closed rules

A candidate is eligible only when all of the following hold:

- the existing RelaySCN / reference / retrieval gates allow snippet recall;
- M2 selected the candidate by a query match rather than mere availability;
- the path is a non-symlink Primary MEM Markdown file inside the scoped root;
- the page has the exact `relaymem.primary_page.v0` front matter and body;
- `memory_layer`, promotion, safety, namespace, path identity, lineage, and
  idempotency metadata are valid;
- exactly one canonical matching Primary index entry and one log entry exist;
- page digest, index/log linkage, namespace, and lineage agree;
- duplicate memory identity is removed;
- item count, character count, and token budget remain bounded.

Malformed, missing, conflicting, unsupported, unsafe, over-budget, wrong-
namespace, or unreconciled candidates are omitted. The adapter never recovers
content from a public projection, trace, queue record, or frontend history.

## Authority and injection

Only the bounded Primary summary is handed to the existing RelayCTX snippet
injection phase. Path, namespace, character, lineage, digest, idempotency, and
retry metadata are not placed in the backend prompt. The inserted message
continues to describe memory as contextual evidence, so the established order
is unchanged:

```text
SOUL / OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  > Secondary MEM
  > RelaySCN
  > Primary MEM
  > Short-term CTX
  > latest input
```

## Public projection

`relaymem.primary_recall_projection.v0` is content-free. It exposes only bounded
status such as attempted/selected counts, Primary-layer counts, scope booleans,
estimated size, injection-candidate presence, and reason IDs. The runtime
artifact containing snippets is request-local and must not be copied into
PipelineNodeResult, generic trace, stdout/stderr, or workflow logs.

## Idempotency

Dispatch identity, M3 write identity, and retrieval deduplication remain
separate. C2/M3 continue to own durable write idempotency. I1 deduplicates the
validated `idempotency_key` before RelayCTX assembly, so duplicate discovery or
a worker retry cannot multiply one memory in the prompt.

## Explicitly unresolved

This Phase does not complete:

- queue scanning, scheduling, or service lifecycle;
- the visible-response-to-background-publication pre-enqueue crash window;
- Secondary MEM consolidation;
- SOUL Lab latest-run / memory observation APIs or Correct operations;
- RelaySOUL mutation;
- TTS, audio, or Live2D execution.
