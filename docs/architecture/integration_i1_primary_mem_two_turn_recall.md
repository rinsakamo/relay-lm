---
relaylm_doc_type: implementation_handoff
relaylm_authority: primary_mem_two_turn_recall
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem
relaylm_update_trigger:
  - Primary recall producer or consumer changes
  - character or namespace scope changes
  - downstream observation or mutation boundary changes
relaylm_not_authoritative_for:
  - queue scanning or daemon lifecycle
  - SOUL Lab observation schema details
  - memory mutation contracts
relaylm_related_authority:
  - phase6c2_one_queued_primary_worker_integration.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - phase_i2_real_soul_lab_observation.md
  - ../PROJECT_STATUS.md
---
# Integration I1: Primary MEM Two-Turn Recall

## Status

Implemented in Phase I-1 and preserved as the authoritative ordinary recall boundary.

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
  -> completed response generation
```

Phase I-2 observes this path but does not replace any I-1 producer, validator, selection, injection, or authority.

## Production ownership

Phase I-1 does not add a queue scanner, scheduler, daemon, or parallel retriever. Existing M2 discovery remains candidate owner. `relaymem_primary_recall` narrows candidates already discovered by M2 and rebuilds the existing RelayCTX snippet handoff from validated bounded Primary summaries.

Character isolation is represented by an opaque partition below the configured RelayMEM root. Both the explicit C2 caller and ordinary request path use `resolve_relaymem_character_store_root()`. Namespace isolation remains an exact property of the canonical Primary page and matching index/log entries.

Session and run identifiers are not new long-term retrieval restrictions. Phase I-2 run correlation is observation evidence only and cannot filter or authorize M2 retrieval.

## Validation and fail-closed rules

A candidate is eligible only when:

- existing RelaySCN/reference/retrieval gates allow snippet recall,
- M2 selected it by query match rather than mere availability,
- path is a non-symlink Primary MEM Markdown file inside the scoped root,
- page has exact `relaymem.primary_page.v0` front matter and body,
- memory layer, promotion, safety, namespace, path identity, lineage, and idempotency metadata are valid,
- exactly one canonical matching Primary index entry and one log entry exist,
- page digest, index/log linkage, namespace, and lineage agree,
- duplicate memory identity is removed,
- item count, character count, and token budget remain bounded.

Malformed, missing, conflicting, unsupported, unsafe, over-budget, wrong-namespace, or unreconciled candidates are omitted. The adapter never recovers content from public projection, trace, queue record, frontend history, or Phase I-2 observation receipt.

## Authority and injection

Only the bounded Primary summary is handed to the existing RelayCTX injection phase. Path, namespace, character, lineage, digest, idempotency, and retry metadata are not placed in the backend prompt.

The established authority order is unchanged:

```text
SOUL / OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  > Secondary MEM
  > RelaySCN
  > Primary MEM
  > Short-term CTX
  > latest input
```

Phase I-2 used-memory evidence is captured only after the existing injection result is known. It cannot mark an unselected candidate as injected or replay memory into a later request.

## Public and runtime-private projection boundary

`relaymem.primary_recall_projection.v0` remains content-free. It exposes only bounded status such as attempted/selected counts, Primary-layer counts, scope booleans, estimated size, injection-candidate presence, and reason IDs.

The runtime artifact containing snippets is request-local and must not be copied into generic `PipelineNodeResult`, trace, stdout/stderr, or workflow logs.

Phase I-2 introduces separate explicit-inspection schemas for Lab Observation. They may return only bounded validated titles/summaries and user-facing outcome state. Those schemas are not substitutes for the I-1 content-free projection and are available only behind the loopback Lab boundary.

## Idempotency

Dispatch identity, M3 write identity, retrieval deduplication, and observation receipt identity remain separate.

C2/M3 own durable write idempotency. I-1 deduplicates validated `idempotency_key` before RelayCTX assembly, so duplicate discovery or worker retry cannot multiply one memory in the prompt. Phase I-2 receipt replay cannot change that result.

## Downstream Phase I-2 — complete

Phase I-2 proves that the completed I-1 path can be inspected after restart without inventing evidence:

- latest completed run is selected deterministically,
- formed memory is resolved from validated Primary page/index/log state,
- held and blocked outcomes remain distinct from retrievable memory,
- used-memory evidence distinguishes candidate, selected, injected, backend-bound, and response-completed stages,
- wrong character and wrong namespace cannot observe another scope,
- observation errors do not change I-1 retrieval or response behavior.

See [Phase I-2 Real SOUL Lab Observation](phase_i2_real_soul_lab_observation.md).

## Next boundary

Phase I-3 auditable Correct is next. It must validate and mutate authoritative memory through a separately reviewed contract, preserve prior state and provenance, and prove later M2 retrieval sees the corrected representation.

Phase I-3 must not rewrite the I-1 recall adapter, use observation receipts as memory authority, or widen into forget, pin, merge, held apply/discard, RelaySOUL mutation, queue scheduling, or daemon lifecycle.

## Explicitly unresolved

Phase I-1 and I-2 do not complete:

- queue scanning, scheduling, or service lifecycle,
- visible-response-to-background-publication pre-enqueue crash recovery,
- Secondary MEM consolidation,
- Correct/forget/pin/merge/held-review mutation,
- RelaySOUL mutation,
- TTS, audio, or Live2D execution,
- static UI bundle serving.

## I1-G boundary

I1-G pre-enqueue background-finalizer durability remains unresolved. Phase I-1 recall and Phase I-2 observation do not recover a turn that never reached durable source and B2 publication.

<!-- phase-i3-auditable-primary-mem-correct -->
## Phase I-3 auditable Primary MEM Correct — complete (2026-06-24)

Phase I-3 completes the first real observe/correct/retrieve loop. A formed Primary MEM observed through Phase I-2 can be corrected through read-only preflight, bounded semantic diff, explicit short-lived-token apply, immutable successor-page publication through the existing M3e boundary, canonical M3f/M3g index/log convergence, and immutable audit receipt finalization. Existing M2 retrieval resolves only the corrected current revision and existing RelayCTX injection remains the sole prompt path.

Character/namespace isolation, stable logical memory identity, no-clobber publication, exact operation idempotency, one-winner revision fencing, crash recovery, and historical used-memory integrity are preserved. Correction reason, audit receipt, paths, digests, lineage, queue/lease state, and prior full pages are not retrieval inputs or public prompt content.

Authority and exact contracts: `docs/architecture/phase_i3_auditable_primary_mem_correct.md`.

Still separate and unresolved: the I1-G process-exit window after visible-response delivery but before background-finalizer protected-source and B2 queue publication. Phase I-3 does not implement forget, pin/unpin, merge, held apply/discard, Secondary MEM consolidation, RelaySOUL mutation, queue scanner/scheduler/daemon, static UI serving, or TTS/audio/avatar execution.

