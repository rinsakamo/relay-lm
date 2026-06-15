# RelayLM Pipeline Implementation Plan

## Purpose

This document is the source of truth for RelayLM pipeline implementation status, phase sequencing, and the next safe boundary.

It does not redefine component ownership. Stable ownership and canonical pipeline order live in [Pipeline Responsibility Design](pipeline_responsibility_design.md). Detailed schemas and behavior live in dedicated module and contract documents.

## Status legend

- **complete**: the intended bounded phase contract is implemented and protected by smoke coverage.
- **mostly complete**: the main boundary is implemented; only small compatibility or safety follow-ups remain.
- **in progress**: part of the bounded phase is implemented, while named apply/runtime behavior remains intentionally absent.
- **planned**: design direction is fixed, but the runtime boundary is not yet implemented.
- **deferred**: intentionally outside the current near-term sequence.

## Current project position

```text
Current project phase: Phase 5-C — in progress

Completed foundations:
  Phase 1 app.py/PipelineContext stabilization
  Phase 2 primary documentation consolidation
  Phase 3 main RelayCTX Repack separation
  Phase 4 RelayINT alias/split boundary
  Phase 4.5 PipelineNodeResult scaffold
  Phase 5-A pure non-stream RelayCTX Unpack
  Phase 5-B gated non-stream runtime Unpack

Current active boundary:
  managed-route client evidence and instruction-cache preflight

Not yet enabled:
  managed-route message-array replacement
  cache-hit RelaySCN state apply
  cache-miss first-pass instruction evidence apply
  typed client-instruction output parse and validation
  instruction-cache write
```

Late fixes to an earlier phase do not roll the project back. Phase numbers identify dependency boundaries rather than a strict waterfall.

## Current caveats

- RelayRUN still acts primarily through request-level artifacts, diagnostics, recovery summaries, and checkpoint-like records; full per-node cross-cutting orchestration remains later work.
- Historical `relayref.py` implementation/artifact names remain as compatibility surfaces for input-side reference-repair behavior exposed through RelayINT-facing wrappers.
- RelayCTX Unpack supports a pure parser and a gated non-stream runtime boundary. Stream Unpack remains deferred to Phase 5.5.
- RelayCTX Repack owns the main backend-bound payload mutation phases, while top-level orchestration and backend-response handling remain distributed across `app.py` and runtime helpers.
- Client-message authority work is deliberately diagnostics-only or runtime-private/read-only until the apply boundary is implemented.
- RelayREF remains planned as a lightweight output-side observer; it is not an answer-grading second LLM.

## Phase order

### Phase 1: `app.py` lightweight separation — mostly complete

Implemented:

- `PipelineContext` is the shared request-local coordination object.
- `original_payload` and `forwarded_payload` are separated.
- forwarded-payload replacements use explicit mutation methods and reasons.
- detached runtime-private and Unpack candidates can be held request-locally.
- grouped diagnostics mapping is separated through `diagnostics_builder.py` and related helpers.
- short-circuit, trace, diagnostics, and RelayRUN artifact behavior remain explicit.

Remaining posture:

- allow only bounded safety or maintainability fixes,
- do not add new semantic ownership to `app.py`,
- move new boundaries into dedicated modules/helpers.

### Phase 2: documentation consolidation — substantially complete

Implemented:

- canonical pipeline ownership and INT/REF timing are documented,
- implementation status is separated from responsibility ownership,
- client history and client instruction authority contracts are documented,
- product-origin and superseded design documents are archived with redirects,
- useful historical principles are migrated to current owner documents,
- runtime operational requirements, AI character product principles, and RelaySOUL update cadence have dedicated owners,
- architecture, contracts, smoke, MVP, and RelaySOUL indexes are separated.

Ongoing maintenance:

- update this plan when implementation phases land,
- archive only after unique design intent is migrated,
- keep MVP summaries as historical snapshots,
- continue SCN/compile-chain and RelaySOUL lifecycle consolidation as separate docs work.

### Phase 3: RelayCTX Repack boundary hardening — mostly complete

Implemented main separation:

- `relaylm/relayctx_repack.py` owns the main backend-bound payload mutation phases,
- RelayMEM snippet/runtime CTX injection is grouped under Repack,
- token-budget truncation application is grouped under Repack,
- RelayCTX short-term runtime injection apply is grouped under Repack,
- payload replacement reasons remain recorded through `PipelineContext`,
- current system/developer instruction extraction compatibility is preserved,
- unsupported instruction parts are not stringified,
- low-trust instruction evidence can be escaped before XML-like rendering.

Remaining Phase 3 posture:

- no new general prompt mutation should bypass Repack,
- managed-route client-authority apply remains part of Phase 5-C rather than ordinary Repack cleanup,
- active tool transactions and compatibility-sensitive request shapes must remain preserved or blocked.

### Phase 4: RelayINT split / compatibility alias — complete

Implemented:

- input-side reference repair is exposed through RelayINT-facing code,
- historical RelayREF naming remains where compatibility requires it,
- RelayINT Fast Path and quick-clarification planning/preflight artifacts exist behind safe defaults,
- source-node aliases permit migration without breaking old artifacts and smoke tests.

Deferred from Phase 4:

- actual user-visible quick-clarification short-circuit apply,
- Main LLM/backend bypass through node routing,
- complete RelayRUN short-circuit lifecycle.

Those belong to Phase 6 routing/apply work.

### Phase 4.5: PipelineNodeResult scaffold — complete

Implemented:

- `relaylm/pipeline_node_result.py` defines the shared frozen result shape,
- `PipelineContext.node_results` preserves ordered request-local results,
- adapter helpers build content-free summaries,
- trace metadata emits pipeline-node results best-effort,
- upstream and directly recorded downstream results retain deterministic ordering,
- client-authority diagnostics can emit node results without exposing content.

Current limitation:

- most node results remain diagnostics-only,
- node results do not yet universally control runtime routing, fallback, retry, or recovery.

### Phase 5-A: pure non-stream RelayCTX Unpack contract — complete

Implemented:

- pure parser in `relaylm/relayctx_unpack.py`,
- ordinary text pass-through when no marker exists,
- one explicit trailing `<relayctx_working_update>` JSON envelope,
- fixed `relayctx_working_update.v0` schema,
- bounded fields, values, and size,
- fail-closed handling for malformed, repeated, reversed, embedded, oversized, or non-trailing markers,
- safe visible-prefix recovery where possible,
- invalid/ambiguous internal candidates blocked,
- content-free diagnostics and PipelineNodeResult adapter,
- no CTX, MEM, SOUL, or SLP persistence.

Accepted shape:

```text
user-visible response
<relayctx_working_update>
{"schema_version":"relayctx_working_update.v0","ctx_working_update":{...}}
</relayctx_working_update>
```

### Phase 5-B: gated non-stream runtime Unpack — complete

Implemented:

- runtime gates for enable/apply/dry-run/max-size behavior,
- Unpack after successful non-stream backend JSON decode,
- unsupported or disabled paths preserve the provider response,
- apply changes only the supported assistant content field,
- response IDs, model metadata, usage, finish reasons, and unrelated provider fields are preserved,
- accepted updates remain detached request-local candidates,
- direct `relayctx_unpack` node-result recording at the execution boundary,
- no persistence, RelayRUN routing change, or streaming mutation.

Supported runtime shape remains deliberately narrow:

```text
successful non-stream JSON
  + exactly one choice
  + assistant role
  + string content
```

### Phase 5-C: managed-route client authority and instruction cache — in progress

#### Phase 5-C1: client-message canonicalization dry-run — complete

Implemented:

- managed-route-only content-free inspection of current request messages,
- latest valid user-turn detection,
- text and multimodal content-shape classification,
- system/developer instruction counts,
- prior-history counts without copying message content,
- active tool-transaction detection and preservation block,
- `canonicalization_candidate_ready` decision,
- content-free PipelineNodeResult.

This phase does not mutate the payload.

#### Phase 5-C2: instruction extraction, identity, and read-only cache lookup — complete as runtime-private/read-only boundaries

Implemented:

- current system/developer instruction extraction,
- normalized request-local instruction identity/fingerprint preparation,
- route/character-scoped cache identity,
- runtime-private content-bearing identity storage in `PipelineContext`,
- file-backed candidate cache reader with bounded entry size,
- read-only cache lookup with hit/miss/blocked/skipped outcomes,
- dependency-aware identity preparation for extraction or lookup,
- content-free diagnostics that exclude hashes, paths, raw instructions, cache entries, and scene content,
- PipelineNodeResult summaries with `applied=false`.

This phase does not inject cached scene state and does not write cache entries.

#### Phase 5-C3: client-history exclusion preflight — complete as diagnostics-only preflight

Implemented:

- runtime-private preflight over the original payload,
- preservation of the current user message candidate,
- candidate counts for excluded history and preserved client messages,
- pass-through exemption,
- active tool-transaction blocking,
- cache-hit / cache-miss-first-pass / no-instruction resolution modes,
- raw-instruction exclusion candidate state,
- ready / pending / blocked / skipped outcomes,
- content-free diagnostics and node result,
- fixed `payload_mutation_applied=false`.

This phase proves readiness but does not replace `messages` in the backend-bound payload.

#### Phase 5-C4: managed-route apply and typed first-pass artifact — next within Phase 5-C

Required work:

1. Add a dedicated apply boundary that consumes only validated Phase 5-C preflight/runtime-private results.
2. Preserve `pass_through` behavior exactly.
3. Preserve active tool transactions rather than canonicalizing through them.
4. On no-instruction or cache-hit paths, replace client messages with the approved current-turn and RelayLM-owned context shape.
5. On cache hit, inject only a validated allowlisted RelaySCN state projection.
6. On cache miss, include one escaped low-trust current-instruction evidence block for first-pass parsing.
7. Never restore raw prior history/system/developer messages as fallback.
8. Record payload replacement through `PipelineContext` with a stable reason.
9. Keep tool, structured-output, multimodal, and provider-specific compatibility gates fail closed.
10. Keep diagnostics content-free and never expose private hashes/paths/cache bodies.

#### Phase 5-C5: client-instruction output artifact and cache write — planned within Phase 5-C

Required contract:

```text
cache miss
  -> escaped low-trust instruction evidence
  -> Main LLM visible response + separately versioned control artifact
  -> RelayCTX visible/internal separation
  -> strict client-instruction schema and policy validation
  -> normalized RelaySCN cache candidate
  -> independent cache-write gate
```

Constraints:

- do not overload `relayctx_working_update.v0`,
- use a separately versioned artifact such as `client_instruction_parse.v1`,
- accept only allowlisted scene role/context/constraint fields,
- block runtime-policy, tool-authority, safety, persistence, and persona-core override attempts,
- keep durable persona fragments as proposals only,
- keep visible-response delivery independent from cache-write success,
- bound retries and avoid indefinite reparsing,
- write cache only after schema, policy, scope, and provenance validation,
- Phase 5-C does not mutate RelaySOUL.

#### Phase 5-C completion criteria

Phase 5-C is complete only when:

- managed routes exclude prior client history by apply, not only preflight,
- current user multimodal evidence is preserved safely,
- current instruction evidence follows cache-hit/miss rules,
- cache-hit state is validated and injected safely,
- cache-miss first-pass artifact is parsed and validated,
- cache write is independently gated,
- pass-through and compatibility-sensitive requests remain unchanged or explicitly blocked,
- all audit/trace surfaces remain content-free.

### Phase 5.5: Stream Unpack and output segmentation — planned

Start after Phase 5-C typed artifact rules are stable.

Planned:

- streaming token/chunk parsing with non-stream-equivalent semantics,
- early forwarding of safe visible chunks,
- trailing sentinel buffering to prevent partial internal-marker leakage,
- fail-closed marker suppression,
- terminal internal candidate collection,
- TTS-safe output segmentation,
- chunk classification for code, URLs, JSON/YAML, tables, commands, paths, quotes, and parenthetical notes,
- lightweight non-meaning-changing Return-side RelayEMO behavior.

### Phase 6: failure-route table and node-result handling — planned

Planned:

- promote selected PipelineNodeResult outcomes into explicit runtime routes,
- map reasons to continue / skip / short-circuit / fallback / blocked / failed,
- let RelayRUN consume node results incrementally,
- implement safe RelayINT quick-clarification apply through response adapters,
- preserve compatibility with per-node checkpoints,
- include stream and output-adapter failure routes,
- preserve idempotency and duplicate-prevention rules.

### Phase 7: lightweight RelayREF observer — planned

Planned:

- diagnostics-only response checks,
- empty/invalid output detection,
- internal-marker and diagnostic leakage detection,
- bounded scene/policy mismatch warnings,
- observations for Output-side RelaySCN and RelayRUN,
- no default regeneration or visible-output replacement.

### Phase 8: Output-side RelaySCN — planned

Planned:

- next-turn scene transition evaluation,
- recovery hints and persistence-block reasons,
- REF/Unpack observation consumption,
- normal transitions as next-turn state,
- immediate blocking limited to leakage, invalid output, safety-critical, or recovery-critical cases.

### Phase 9: RelayRUN cross-cutting checkpoint layer — planned

Planned:

- per-node started/completed/skipped/blocked/failed reporting,
- persistent checkpoints and resume metadata,
- timeout/retry/skip/fallback policy,
- streaming state and partial-output handling,
- waiting-user action contracts,
- idempotency and duplicate prevention,
- semantic-neutral runtime orchestration,
- visible recovery text routed through the normal output pipeline.

### Phase 10: RelaySLP separation — planned

Planned:

- memory/SOUL compilation outside the normal response path,
- governed raw evidence and lineage,
- retrieval reads separated from SLP writes,
- safety classification and hold/reject/proposal states,
- persistence and approval gates,
- no direct normal-turn MEM or SOUL mutation.

## Failure-route principles

### INT clarification

```text
RelayINT clarification decision
  -> compatibility / scene gates
  -> explicit short-circuit route when enabled
  -> RelayRUN state and artifact
  -> normal output pipeline
```

### MEM retrieval blocked or empty

```text
retrieval miss / empty / blocked
  -> CTX Repack without the blocked memory block
  -> record reasons
  -> continue when the request is not memory-dependent
```

### CTX Repack token pressure

Degrade in this order:

1. remove diagnostics/trace-only context,
2. reduce retrieved memory,
3. reduce optional short-term CTX hints,
4. shorten selected conversation context,
5. block or use an approved safe fallback when no valid payload remains.

### CTX Unpack failure

```text
preserve safely recoverable visible output
block invalid internal candidates
record content-free diagnostics
never expose internal markers
```

### Partial stream/output-adapter failure

```text
preserve safe emitted chunks
block incomplete candidates
record partial-stream state
avoid duplicate replay
prepare recovery when required
```

### REF warning

RelayREF findings remain observations unless an explicit output gate handles invalid output, leakage, or safety-critical mismatch.

## Immediate next boundary

The next implementation slice is **Phase 5-C4 managed-route apply**.

It should remain small:

```text
validated canonicalization / identity / cache lookup / history-exclusion preflight
  -> dedicated apply helper
  -> current-turn-only managed messages
  -> cache-hit validated scene projection OR cache-miss escaped evidence block
  -> PipelineContext payload replacement reason
  -> content-free node result and smoke coverage
```

Do not combine Phase 5-C4 with cache write, RelaySOUL proposals, Stream Unpack, RelayREF, or full RelayRUN routing.
