# RelayLM Pipeline Implementation Plan

## Purpose

This document is the source of truth for RelayLM pipeline implementation status, phase sequencing, dependency boundaries, and the next safe implementation slice.

It does not redefine component ownership. Use [Pipeline Responsibility Design](pipeline_responsibility_design.md) for component responsibilities and canonical target order, and [Current / Target / Migration Guide](current_target_migration_guide.md) for schema/status interpretation.

Detailed schemas and bounded behavior remain in dedicated module and contract documents.

## Status legend

- **complete**: the bounded phase contract is implemented and covered by smoke tests.
- **mostly complete**: the main boundary is implemented; bounded compatibility or safety follow-up remains.
- **in progress**: a named subset is implemented while required behavior remains absent.
- **planned**: design direction exists without runtime implementation.
- **deferred**: intentionally outside the near-term path and not a gate for the active boundary.

## Current project position

```text
Current phase: Phase 5-C — in progress

Completed foundations:
  Phase 1 app.py / PipelineContext stabilization
  Phase 2 documentation consolidation
  Phase 3 main RelayCTX Repack separation
  Phase 4 RelayINT compatibility boundary
  Phase 4.5 PipelineNodeResult scaffold
  Phase 5-A pure non-stream RelayCTX Unpack
  Phase 5-B gated non-stream RelayCTX Unpack
  Phase 5-C1 through 5-C3 diagnostics/read-only foundations
  Phase 5-C1a no-instruction history-exclusion apply slice

Current active boundary:
  complete Phase 5-C4a for instruction-bearing managed requests

Near-term sequence:
  Phase 5-D pre-stream hardening
  Phase 5.5 Stream Unpack and TTS-safe output segmentation

Deferred optimization:
  Phase 5-C4b cache-hit RelaySCN projection
  Phase 5-C5 typed instruction parse and cache write
```

The `5-C1a` label is a late bounded slice. It does not replace the broader `5-C4a` correctness criteria.

Late fixes to an earlier phase do not roll the project back. Phase identifiers represent dependency and authority boundaries rather than a strict waterfall.

Phase 5-C4b and Phase 5-C5 retain their identifiers for design continuity, but they do not block Phase 5-D or Phase 5.5 after the Phase 5-C correctness boundary is complete.

## Correctness versus optimization dependency rule

The client-authority work contains two separate concerns and must not treat them as one blocking phase.

```text
Correctness boundary:
  exclude prior client history on managed routes
  preserve the validated current turn
  preserve RelayLM-owned context
  carry current client instruction only as bounded low-trust evidence when required
  preserve or explicitly block compatibility-sensitive transactions

Optimization boundary:
  avoid repeated instruction parsing through cache-hit RelaySCN projection
  parse a typed first-pass instruction artifact
  write validated instruction-cache entries
```

Only the correctness boundary is required before Stream Unpack work begins.

## Current caveats

- Current profile compilation still runs before normalized target SCN/INT/Retrieval handoffs.
- Current compile behavior has both the typed `CompileApplyDecision` and a separate content-free `mvp-ctx-apply-0` diagnostics artifact; the complete authority-aware v1 taxonomy is not implemented.
- The no-instruction history-exclusion apply supports the current `memory_light` compiler layout only.
- Client system/developer instruction evidence is not supported by that apply contract.
- History-exclusion apply is default-off and dry-run by default.
- Explicit actual apply fails closed before backend forwarding when no exact applied result exists.
- Full target Runtime Compile Gate route-authority, forwarded-payload-source, managed fallback, and complete blocked-state artifacts are not implemented.
- RelayRUN still acts primarily through request-level artifacts, diagnostics, recovery summaries, and checkpoint-like records; full per-node cross-cutting orchestration remains later work.
- Recovery-related settings are default-off, but the detailed recovery artifact chain is still constructed eagerly on the ordinary request path.
- Historical `relayref.py` implementation and artifact names remain as compatibility surfaces for input-side reference repair exposed through RelayINT-facing wrappers.
- RelayCTX Unpack supports a pure parser and a gated non-stream runtime boundary. Stream Unpack remains planned for Phase 5.5.
- RelayCTX Repack owns the main backend-bound payload mutation phases, while top-level orchestration and backend-response handling remain distributed across `app.py` and runtime helpers.
- Instruction-cache lookup is an optional optimization boundary; it is not required to establish managed-route history authority.
- Token estimation still uses a single `chars_per_token` ratio whose default is not conservative enough for Japanese/CJK-heavy text.
- RelayREF remains planned as a lightweight output-side observer; it is not an answer-grading second LLM.
- RelayLM owns safe visible-text segmentation in the target architecture, but it does not own external TTS, ASR, avatar, or frontend execution.
- RelaySLP and RelaySOUL actual persistence/apply paths remain absent.

## Phase 1: `app.py` and PipelineContext — mostly complete

Implemented:

- `PipelineContext` is the shared request-local coordination object.
- original and forwarded payloads are separated.
- forwarded-payload replacements use explicit mutation methods and reasons.
- runtime-private candidates and ordered node results remain request-local.
- detached Unpack and client-authority candidates can be held without entering generic trace.
- grouped diagnostics and trace handoffs are separated from payload content.
- short-circuit and RelayRUN artifact behavior remain explicit.

Remaining posture:

- allow only bounded safety or maintainability fixes in `app.py`,
- do not add new semantic ownership to `app.py`,
- place new semantic boundaries in dedicated modules/helpers.

## Phase 2: documentation consolidation — substantially complete

Implemented:

- canonical pipeline ownership and INT/REF timing,
- implementation status separated from responsibility ownership,
- client history and instruction authority contracts,
- archive and compatibility redirect rules,
- dedicated architecture, contract, smoke, MVP, and RelaySOUL indexes,
- current-state summary and implementation plan,
- Current / Compatibility / Target / Migration interpretation rules.

Ongoing maintenance:

- keep current, compatibility, target, and migration material explicitly labeled,
- keep active schemas aligned with implemented producers and consumers,
- update this plan when phases land or are resequenced,
- archive only after unique design intent is migrated,
- keep MVP summaries as historical snapshots.

## Phase 3: RelayCTX Repack — mostly complete

Implemented:

- main backend-bound payload mutation phases live under `relayctx_repack.py`,
- RelayMEM snippet/runtime CTX injection is grouped under Repack,
- token-budget truncation application is grouped under Repack,
- RelayCTX short-term runtime injection apply is grouped under Repack,
- payload replacement reasons remain visible through `PipelineContext`,
- current system/developer instruction extraction compatibility is preserved,
- unsupported instruction parts are not blindly stringified,
- low-trust instruction evidence can be escaped before XML-like rendering.

Remaining rule:

- no new general prompt mutation bypasses Repack or managed-authority gates,
- active tool transactions and compatibility-sensitive request shapes remain preserved or explicitly blocked.

## Phase 4: RelayINT compatibility boundary — complete

Implemented:

- input-side reference repair is exposed through RelayINT-facing wrappers,
- historical RelayREF names remain only where compatibility requires them,
- RelayINT Fast Path and quick-clarification planning/preflight artifacts are default-off,
- source-node aliases permit migration without breaking existing artifacts and smoke tests.

Deferred:

- actual user-visible quick-clarification short circuit,
- Main LLM/backend bypass through explicit node routing,
- complete RelayRUN short-circuit lifecycle.

Those belong to later routing/apply work.

## Phase 4.5: PipelineNodeResult — complete

Implemented:

- common frozen node-result shape,
- ordered request-local collection,
- typed content-free projections,
- direct input-side node ordering,
- best-effort trace metadata projection,
- deterministic ordering for upstream and directly recorded downstream results.

Current limitation:

- most node results remain diagnostics-only,
- node results do not yet universally control runtime routing, retry, fallback, or recovery.

## Phase 5-A: pure non-stream RelayCTX Unpack — complete

Implemented:

- pure parser in `relaylm/relayctx_unpack.py`,
- ordinary text pass-through when no marker exists,
- exactly one trailing supported `<relayctx_working_update>` JSON envelope,
- fixed `relayctx_working_update.v0` schema,
- bounded fields, values, and size,
- fail-closed handling for malformed, repeated, reversed, embedded, oversized, or non-trailing markers,
- safe visible-prefix preservation where possible,
- invalid/ambiguous internal candidates blocked,
- detached candidate storage,
- content-free diagnostics and PipelineNodeResult adapter,
- no CTX, MEM, SOUL, or SLP persistence.

Accepted shape:

```text
user-visible response
<relayctx_working_update>
{"schema_version":"relayctx_working_update.v0","ctx_working_update":{...}}
</relayctx_working_update>
```

## Phase 5-B: gated non-stream RelayCTX Unpack — complete

Implemented:

- enable/apply/dry-run/max-size gates,
- Unpack after successful non-stream backend JSON decode,
- unsupported or disabled paths preserve the provider response,
- apply changes only the supported assistant content field,
- response IDs, model metadata, usage, finish reasons, and unrelated provider fields remain preserved,
- accepted updates remain detached request-local candidates,
- direct node-result recording at the execution boundary,
- no persistence, RelayRUN route change, or streaming mutation.

Supported runtime shape remains deliberately narrow:

```text
successful non-stream JSON
  + exactly one choice
  + assistant role
  + string content
```

## Phase 5-C: managed-route client authority — in progress

Phase 5-C closes when the managed-route history-authority correctness boundary is safely applied. Cache projection and write remain a deferred optimization track.

### Phase 5-C1: client-message canonicalization — complete as dry-run

Implemented:

- managed-route-only content-free inspection,
- latest valid user-turn detection,
- text and multimodal shape classification,
- system/developer instruction counts,
- prior-history counts without copying message content,
- active tool-transaction detection and preservation block,
- `canonicalization_candidate_ready` decision,
- content-free node result.

No payload mutation occurs in this phase.

### Phase 5-C1a: no-instruction history-exclusion apply — complete as bounded default-off slice

Implemented contract:

```text
client_history_exclusion_apply.v0
```

Producers:

```text
relaylm.client_history_exclusion_apply.build_client_history_exclusion_apply
relaylm.client_history_exclusion_apply_runtime.run_client_history_exclusion_apply_runtime
```

Implemented behavior:

- requires a managed `memory_light` compiled payload,
- consumes the typed history-exclusion preflight,
- supports only `instruction_resolution_mode=none`,
- requires zero client system/developer messages,
- retains exactly one RelayLM-owned compiled prefix message,
- retains the detached validated current-user message,
- creates a request-local payload candidate in dry-run,
- replaces `PipelineContext.forwarded_payload` only for an exact actual-applied result,
- records a typed content-free node result,
- is idempotent within one request,
- exempts explicit `pass_through` routes.

Default posture:

```text
client_history_exclusion_apply_enabled=false
client_history_exclusion_apply_dry_run_only=true
```

Backend-forward rule:

```text
explicit actual apply + managed route
  + missing / blocked / skipped / ready-only / otherwise non-applied result
  -> block backend forward
```

Runtime exceptions are projected into a blocked result with a bounded reason. There is no separate current `failed` status in `client_history_exclusion_apply.v0`.

This slice does not implement:

- instruction-bearing managed apply,
- cache-hit RelaySCN injection,
- cache-miss low-trust instruction evidence,
- typed instruction parse,
- cache write,
- Stream Unpack.

### Phase 5-C2: instruction identity and read-only cache lookup — complete

Implemented:

- current system/developer instruction extraction,
- request-local identity/fingerprint preparation,
- route/character-scoped cache identity,
- runtime-private content-bearing identity storage in `PipelineContext`,
- bounded file-backed read-only lookup,
- hit/miss/blocked/skipped outcomes,
- dependency-aware identity preparation,
- content-free evidence excluding hashes, paths, raw instructions, cache entries, and scene content.

Not implemented:

- cached scene-state injection,
- cache entry write.

### Phase 5-C3: history-exclusion preflight — complete

Implemented:

- typed request-local preflight over the original payload,
- current-user message candidate,
- history-exclusion counts,
- pass-through exemption,
- active transaction block,
- cache-hit/cache-miss/no-instruction resolution classification,
- raw-instruction exclusion candidate state,
- ready/pending/blocked/skipped outcomes,
- content-free projection,
- fixed `payload_mutation_applied=false`.

Preflight does not itself mutate `messages`.

### Phase 5-C4a: broader managed-route correctness path — in progress

Remaining required work:

1. Support instruction-bearing managed requests without forwarding raw system/developer authority.
2. Carry at most one escaped, bounded, explicitly low-trust current-instruction evidence block when policy requires it.
3. Preserve current text and multimodal user content.
4. Preserve or block active tool/structured-output transactions coherently.
5. Build only RelayLM-owned managed payloads.
6. Keep every replacement recorded through `PipelineContext`.
7. Preserve the current no-instruction apply contract and forward gate.
8. Keep generic diagnostics content-free.
9. Never restore raw prior client history as fallback.

Non-goals:

- cache-hit RelaySCN projection,
- typed instruction-output parsing,
- cache write,
- RelaySOUL mutation,
- Stream Unpack,
- RelayREF,
- full RelayRUN routing.

### Phase 5-C completion criteria

The correctness boundary is complete when:

- no-instruction and supported instruction-bearing managed requests exclude prior client history by apply,
- the validated current turn is preserved,
- compatible current multimodal evidence is preserved,
- current instruction evidence remains bounded, escaped, and low-trust,
- raw client instructions are not backend authority,
- `pass_through` remains unchanged,
- unsupported compatibility shapes are unchanged or blocked explicitly,
- every mutation is recorded,
- default audit/trace surfaces remain content-free.

Cache projection, typed parsing, and cache write are not completion gates.

## Phase 5-D: pre-stream hardening — planned

### Phase 5-D1: CJK-aware token estimation

Required work:

- replace the single `chars_per_token=4` assumption with deterministic bounded estimation,
- distinguish CJK-heavy and ASCII-heavy input,
- use conservative rounding,
- avoid claiming tokenizer-exact counts,
- cover Japanese, ASCII, mixed-language text, emoji, punctuation, Markdown, and code,
- protect token-budget truncation from underestimating CJK-heavy input.

A runtime-specific tokenizer may be added later but is not required for this phase.

### Phase 5-D2: lazy RelayRUN recovery-detail construction

Required work:

- keep the minimal request/run/node/backend summary available on the ordinary path,
- do not eagerly construct the full recovery artifact chain when every recovery feature is disabled and no recovery-relevant state exists,
- construct recovery detail when any of these is true:
  - a recovery-related config is enabled,
  - a node is failed, blocked, or waiting for the user in a recovery-relevant way,
  - checkpoint persistence requires the detail,
  - explicit full trace diagnostics require the detail,
- preserve existing fail-closed, content-free, and default-off contracts,
- avoid visible response changes,
- add smoke coverage for both the minimal ordinary path and expanded recovery path.

## Phase 5.5: Stream Unpack and output segmentation — planned

Start after Phase 5-C4a and Phase 5-D are stable. Phase 5-C4b and Phase 5-C5 are not prerequisites.

Planned:

- streaming token/chunk parsing with non-stream-equivalent semantics,
- early forwarding of safe visible chunks,
- trailing sentinel buffering to prevent partial internal-marker leakage,
- fail-closed marker suppression,
- terminal internal candidate collection,
- incomplete candidate blocking,
- partial-stream cancellation and disconnect handling,
- duplicate-emission prevention,
- TTS-safe output segmentation,
- chunk classification for code, URLs, JSON/YAML, tables, commands, paths, quotes, and parenthetical notes,
- lightweight non-meaning-changing Return-side RelayEMO hints,
- content-free stream diagnostics and node results.

RelayLM's output contract should expose safe visible segments and segment metadata. External TTS and avatar runtimes remain integration consumers rather than RelayLM-owned model runtimes.

## External realtime validation — planned after Phase 5.5

Validate the real-time path without moving frontend, TTS, or avatar ownership into RelayLM:

```text
frontend
  -> RelayLM streaming endpoint
  -> OpenAI-compatible backend
  -> safe visible segments
  -> external TTS adapter
  -> external avatar/runtime consumer
```

Validation should cover:

- first-token latency,
- first-sentence latency,
- first-TTS-enqueue latency,
- marker non-leakage,
- segment ordering,
- cancellation/disconnect,
- duplicate prevention,
- ordinary fallback behavior.

## Phase 6: failure-route table and node-result handling — planned

- promote selected PipelineNodeResult outcomes into explicit runtime routes,
- map reasons to continue/skip/short-circuit/fallback/blocked/failed orchestration states,
- let RelayRUN consume node results incrementally,
- implement safe RelayINT quick-clarification apply through response adapters,
- preserve compatibility with per-node checkpoints,
- include stream and output-adapter failure routes,
- preserve idempotency and duplicate-prevention rules.

## Phase 7: lightweight RelayREF observer — planned

- diagnostics-only post-generation checks,
- empty/invalid output detection,
- internal-marker and diagnostic leakage detection,
- bounded scene/policy mismatch observations,
- observations for Output-side RelaySCN and RelayRUN,
- no default regeneration or visible-output replacement.

## Phase 8: Output-side RelaySCN — planned

- next-turn transition evaluation,
- recovery hints and persistence-block reasons,
- REF/Unpack observation consumption,
- normal transitions as next-turn state,
- immediate blocking limited to leakage, invalid output, safety-critical, or recovery-critical cases,
- no general output rewriting.

## Phase 9: RelayRUN cross-cutting orchestration — planned

- per-node started/completed/skipped/blocked/failed reporting,
- persistent checkpoints and resume metadata,
- timeout/retry/skip/fallback policy,
- stream state and partial-output handling,
- waiting-user action contracts,
- idempotency and duplicate prevention,
- semantic-neutral runtime orchestration,
- visible recovery text routed through the normal output pipeline.

## Phase 10: RelaySLP separation — planned

- memory/SOUL compilation outside the normal response path,
- governed raw evidence and lineage,
- retrieval reads separated from SLP writes,
- safety classification and hold/reject/proposal states,
- persistence and approval gates,
- no direct normal-turn MEM or SOUL mutation.

## Deferred optimization track

### Phase 5-C4b: cache-hit RelaySCN projection — deferred

Future work:

- validate cache entries against exact schema, policy, route, character, and version scope,
- inject only an allowlisted RelaySCN state projection,
- never inject raw cached instructions or opaque cache bodies,
- keep miss, invalid, stale, and unsupported entries fail closed,
- keep visible response delivery independent from cache availability.

### Phase 5-C5: typed client-instruction artifact and cache write — deferred

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

## RelaySOUL posture during core-output phases

Until Stream Unpack and the external realtime path are stable:

- preserve existing RelaySOUL contracts, approval gates, revision rules, and rollback design,
- allow bounded correctness and safety fixes,
- keep current `mvp-soul-0` five-file behavior labeled as compatibility,
- do not expand normal-chat runtime persona mutation,
- do not enable actual apply, rollback, or persistence execution,
- do not make new RelaySOUL governance work a dependency of Phase 5.5.

## Failure-route principles

### RelayINT clarification

```text
RelayINT clarification decision
  -> compatibility / scene gates
  -> explicit short-circuit route when enabled
  -> RelayRUN state and artifact
  -> normal output pipeline
```

A user-visible clarification must not bypass the ordinary output policy and adapter path.

### RelayMEM retrieval blocked or empty

```text
retrieval miss / empty / blocked
  -> CTX Repack without the blocked memory block
  -> record bounded reasons
  -> continue when the request is not memory-dependent
```

Retrieval remains read-only and does not repair itself by writing memory.

### RelayCTX Repack token pressure

Degrade in this order:

1. remove diagnostics/trace-only context,
2. reduce retrieved memory,
3. reduce optional short-term CTX hints,
4. shorten selected conversation context,
5. block or use an approved authority-safe managed fallback when no valid payload remains.

Raw client history is not the terminal fallback for a managed route.

### RelayCTX Unpack failure

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

### RelayREF warning

RelayREF findings remain observations unless an explicit output gate handles invalid output, leakage, or a safety-critical mismatch.

## Immediate next boundary

The next implementation slice is the instruction-bearing remainder of **Phase 5-C4a**.

Keep it small:

```text
validated client-message evidence
  + history-exclusion preflight
  -> dedicated managed-route apply helper
  -> current-turn-only client message preservation
  -> RelayLM-owned context preservation
  -> at most one escaped low-trust current-instruction evidence block
  -> PipelineContext payload replacement reason
  -> content-free node result and smoke coverage
```

Do not combine Phase 5-C4a with cache-hit projection, typed instruction parsing, cache write, RelaySOUL proposals, Stream Unpack, RelayREF, or full RelayRUN routing.
