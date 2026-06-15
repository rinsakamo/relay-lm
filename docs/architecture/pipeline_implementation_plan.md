# RelayLM Pipeline Implementation Plan

## Purpose

This document is the source of truth for RelayLM pipeline implementation status, phase sequencing, and the next safe boundary.

It does not redefine component ownership. Stable ownership and canonical pipeline order live in [Pipeline Responsibility Design](pipeline_responsibility_design.md). Detailed schemas and behavior live in dedicated module and contract documents.

## Status legend

- **complete**: the intended bounded phase contract is implemented and protected by smoke coverage.
- **mostly complete**: the main boundary is implemented; only small compatibility or safety follow-ups remain.
- **in progress**: part of the bounded phase is implemented, while named apply/runtime behavior remains intentionally absent.
- **planned**: design direction is fixed, but the runtime boundary is not yet implemented.
- **deferred**: intentionally outside the current near-term sequence and not a gate for the next active phase.

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
  Phase 5-C1 through 5-C3 diagnostics/read-only foundations

Current active boundary:
  Phase 5-C4a managed-route history-exclusion apply

Near-term sequence after 5-C4a:
  Phase 5-D pre-stream hardening
  Phase 5.5 Stream Unpack and TTS-safe output segmentation

Deferred optimization track:
  Phase 5-C4b cache-hit RelaySCN projection
  Phase 5-C5 typed client-instruction artifact and cache write
```

Late fixes to an earlier phase do not roll the project back. Phase numbers identify dependency boundaries rather than a strict waterfall.

Phase 5-C4b and Phase 5-C5 retain their identifiers for design continuity, but they no longer block Phase 5.5.

## Current caveats

- RelayRUN still acts primarily through request-level artifacts, diagnostics, recovery summaries, and checkpoint-like records; full per-node cross-cutting orchestration remains later work.
- Recovery-related settings are default-off, but the detailed recovery artifact chain is still constructed eagerly on the normal request path.
- Historical `relayref.py` implementation/artifact names remain as compatibility surfaces for input-side reference-repair behavior exposed through RelayINT-facing wrappers.
- RelayCTX Unpack supports a pure parser and a gated non-stream runtime boundary. Stream Unpack remains planned for Phase 5.5.
- RelayCTX Repack owns the main backend-bound payload mutation phases, while top-level orchestration and backend-response handling remain distributed across `app.py` and runtime helpers.
- Client-message authority work is diagnostics-only or runtime-private/read-only until Phase 5-C4a lands.
- Instruction-cache lookup is an optional optimization boundary; it is not required to establish managed-route history authority.
- Token estimation still uses a single `chars_per_token` ratio whose default is not conservative enough for Japanese/CJK-heavy text.
- RelayREF remains planned as a lightweight output-side observer; it is not an answer-grading second LLM.
- RelayLM owns safe visible-text segmentation, but it does not own the external TTS, ASR, avatar, or frontend runtime.

## Revised dependency rule

The client-authority work contains two different concerns and must not treat them as one blocking phase.

```text
Correctness boundary:
  exclude prior client history on managed routes
  preserve the validated current turn
  preserve RelayLM-owned context
  carry current client instruction only as bounded low-trust evidence when required

Optimization boundary:
  avoid repeated instruction parsing through cache-hit RelaySCN projection
  parse a typed first-pass instruction artifact
  write validated instruction-cache entries
```

Only the correctness boundary is required before Stream Unpack work begins.

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

- update this plan when implementation phases land or are resequenced,
- archive only after unique design intent is migrated,
- keep MVP summaries as historical snapshots,
- continue SCN/compile-chain and RelaySOUL lifecycle consolidation as separate documentation work.

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

### Phase 5-C: managed-route client authority core — in progress

Phase 5-C now closes when the managed-route history-authority correctness boundary is applied safely. Instruction-cache apply and write remain a deferred optimization track.

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

#### Phase 5-C4a: managed-route history-exclusion apply — next

Required work:

1. Add a dedicated apply boundary that consumes only validated canonicalization and history-exclusion preflight results.
2. Preserve `pass_through` behavior exactly.
3. Preserve active tool transactions rather than canonicalizing through them.
4. Replace prior client history with the approved current user turn and RelayLM-owned context shape.
5. Preserve current text and multimodal user content without flattening or stringifying unsupported parts.
6. When current system/developer evidence is required for the current scene, include at most one escaped, bounded, explicitly low-trust evidence block.
7. Do not require cache-hit state injection or a typed first-pass output artifact for this apply boundary.
8. Never restore raw prior history as fallback.
9. Record payload replacement through `PipelineContext` with a stable reason.
10. Keep tool, structured-output, multimodal, and provider-specific compatibility gates fail closed.
11. Keep diagnostics content-free and never expose private hashes, paths, raw instructions, or cache bodies.

Phase 5-C4a non-goals:

- cache-hit RelaySCN projection,
- typed client-instruction output parsing,
- instruction-cache write,
- RelaySOUL proposals or mutation,
- Stream Unpack,
- RelayREF implementation,
- full RelayRUN route-table promotion.

#### Phase 5-C core completion criteria

Phase 5-C core is complete when:

- managed routes exclude prior client history by apply, not only preflight,
- the validated current user turn is preserved,
- current multimodal evidence is preserved safely,
- optional current instruction evidence is escaped, bounded, low-trust, and not forwarded as backend-authoritative system/developer messages,
- `pass_through` remains unchanged,
- compatibility-sensitive requests remain unchanged or explicitly blocked,
- every payload replacement is recorded through `PipelineContext`,
- all audit/trace surfaces remain content-free.

Cache-hit projection, typed instruction parsing, and cache write are not Phase 5-C core completion gates.

### Phase 5-D: pre-stream runtime hardening — planned

Phase 5-D is intentionally narrow and should land after Phase 5-C4a and before Phase 5.5 runtime apply work.

#### Phase 5-D1: CJK-aware token estimation

Required work:

- replace the single-language `chars_per_token=4` assumption with a bounded policy that distinguishes CJK-heavy text from ASCII-heavy text,
- keep estimation deterministic and dependency-light,
- avoid claiming tokenizer-exact counts,
- use conservative rounding for Japanese/CJK text,
- add Japanese, ASCII, mixed-language, emoji, punctuation, Markdown, and code smoke coverage,
- protect token-budget truncation from underestimating CJK-heavy input.

A runtime-specific tokenizer may be added later, but it is not required for this phase.

#### Phase 5-D2: lazy RelayRUN recovery-detail construction

Required work:

- keep the minimal request/run/node/backend summary available on the ordinary path,
- do not eagerly construct the full recovery artifact chain when every recovery feature is disabled and no recovery-relevant state exists,
- construct recovery detail when any of these is true:
  - a recovery-related config is enabled,
  - a node is failed, blocked, or waiting for the user in a recovery-relevant way,
  - checkpoint persistence requires the detail,
  - explicit full trace diagnostics require the detail,
- preserve existing fail-closed, content-free, and default-off contracts,
- avoid changing visible response behavior in this phase,
- add smoke coverage for both the minimal ordinary path and the expanded recovery path.

### Phase 5.5: Stream Unpack and output segmentation — planned

Start after Phase 5-C4a and Phase 5-D are stable. Phase 5-C4b and Phase 5-C5 are not prerequisites.

Planned:

- streaming token/chunk parsing with non-stream-equivalent semantics,
- early forwarding of safe visible chunks,
- trailing sentinel buffering to prevent partial internal-marker leakage,
- fail-closed marker suppression,
- terminal internal candidate collection,
- partial-stream cancellation and disconnect handling,
- duplicate-emission prevention,
- TTS-safe output segmentation,
- chunk classification for code, URLs, JSON/YAML, tables, commands, paths, quotes, and parenthetical notes,
- lightweight non-meaning-changing Return-side RelayEMO behavior,
- content-free stream diagnostics and node results.

RelayLM's output contract should expose safe visible segments and segment metadata. External TTS and avatar runtimes remain integration consumers rather than RelayLM-owned model runtimes.

### External end-to-end validation — planned after Phase 5.5

Validate the real-time path without moving frontend, TTS, or avatar ownership into RelayLM:

```text
frontend
  -> RelayLM streaming endpoint
  -> OpenAI-compatible backend
  -> safe visible segments
  -> external TTS adapter
  -> external avatar/runtime consumer
```

Validation should cover first-speech latency, marker non-leakage, segment ordering, cancellation, and ordinary fallback behavior.

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

### Deferred optimization track: instruction-cache apply and write

The following work remains valid but is deferred until the core streaming path and external end-to-end validation are stable.

#### Phase 5-C4b: cache-hit RelaySCN projection — deferred

Future work:

- validate cache entries against exact schema, policy, route, character, and version scope,
- inject only an allowlisted RelaySCN state projection,
- never inject raw cached instructions or opaque cache bodies,
- keep miss, invalid, stale, and unsupported entries fail closed,
- keep visible response delivery independent from cache availability.

#### Phase 5-C5: typed client-instruction output artifact and cache write — deferred

Future contract:

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
- never mutate RelaySOUL from normal chat.

## RelaySOUL posture during the core-output phases

Until Stream Unpack and the external real-time path are stable:

- preserve existing RelaySOUL contracts, approval gates, revision rules, and rollback design,
- allow bounded correctness and safety fixes,
- do not expand normal-chat runtime persona mutation,
- do not make new RelaySOUL governance work a dependency of Phase 5.5.

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

The next implementation slice is **Phase 5-C4a managed-route history-exclusion apply**.

It should remain small:

```text
validated canonicalization / history-exclusion preflight
  -> dedicated managed-route apply helper
  -> current-turn-only client message preservation
  -> RelayLM-owned context preservation
  -> optional escaped low-trust current-instruction evidence
  -> PipelineContext payload replacement reason
  -> content-free node result and smoke coverage
```

Do not combine Phase 5-C4a with cache-hit projection, typed instruction parsing, cache write, RelaySOUL proposals, Stream Unpack, RelayREF, or full RelayRUN routing.
