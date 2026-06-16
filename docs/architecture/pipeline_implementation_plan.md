# RelayLM Pipeline Implementation Plan

## Purpose

This document is the source of truth for implementation status, phase sequencing, and the next safe boundary.

It does not redefine ownership. Use [Pipeline Responsibility Design](pipeline_responsibility_design.md) for component responsibilities and [Current / Target / Migration Guide](current_target_migration_guide.md) for schema/status interpretation.

## Status legend

- **complete**: the bounded phase contract is implemented and covered by smoke tests.
- **mostly complete**: the main boundary is implemented; bounded follow-up remains.
- **in progress**: a named subset is implemented while required behavior remains absent.
- **planned**: design direction exists without runtime implementation.
- **deferred**: intentionally outside the near-term path.

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
  Phase 5.5 Stream Unpack and TTS-safe segmentation

Deferred optimization:
  Phase 5-C4b cache-hit RelaySCN projection
  Phase 5-C5 typed instruction parse and cache write
```

The `5-C1a` label is a late bounded slice. It does not replace the broader `5-C4a` correctness criteria.

## Current caveats

- Current profile compilation still runs before normalized target SCN/INT/Retrieval handoffs.
- The no-instruction history-exclusion apply supports the current `memory_light` compiler layout only.
- Client system/developer instruction evidence is not supported by that apply contract.
- History-exclusion apply is default-off and dry-run by default.
- Explicit actual apply fails closed before backend forwarding when no exact applied result exists.
- Full target Runtime Compile Gate route-authority and managed fallback artifacts are not implemented.
- RelayCTX Unpack is non-stream only; Stream Unpack remains planned.
- RelayREF remains a planned output observer.
- RelayRUN remains mostly request-level rather than complete per-node orchestration.
- RelaySLP and RelaySOUL actual persistence/apply paths remain absent.
- Token estimation still uses a single character-ratio heuristic.

## Phase 1: `app.py` and PipelineContext — mostly complete

Implemented:

- `PipelineContext` preserves original and forwarded payloads.
- payload replacements use explicit methods and reasons.
- runtime-private candidates and ordered node results are request-local.
- diagnostics and trace handoffs are separated from payload content.

Rule:

- new semantic behavior belongs in dedicated modules, not in `app.py`.

## Phase 2: documentation consolidation — substantially complete

Implemented:

- canonical pipeline ownership and INT/REF timing,
- client history and instruction authority contracts,
- archive and compatibility redirect rules,
- dedicated architecture, contract, smoke, MVP, and RelaySOUL indexes,
- current-state summary and implementation plan.

Ongoing:

- keep current, compatibility, target, and migration material explicitly labeled,
- keep active schemas aligned with implemented producers and consumers.

## Phase 3: RelayCTX Repack — mostly complete

Implemented:

- main backend-bound payload mutation phases live under `relayctx_repack.py`,
- RelayMEM and short-term CTX injection are grouped under Repack,
- token-budget application is grouped under Repack,
- payload replacement reasons remain visible through `PipelineContext`,
- unsupported instruction parts are not blindly stringified.

Remaining rule:

- no new general prompt mutation bypasses Repack or the managed-authority gates.

## Phase 4: RelayINT compatibility boundary — complete

Implemented:

- input-side reference repair is exposed through RelayINT-facing wrappers,
- historical RelayREF names remain only where compatibility requires them,
- Fast Path and quick-clarification planning/preflight artifacts are default-off.

Deferred:

- user-visible quick-clarification short circuit,
- Main LLM bypass through explicit routing,
- full RelayRUN short-circuit lifecycle.

## Phase 4.5: PipelineNodeResult — complete

Implemented:

- common frozen node-result shape,
- ordered request-local collection,
- typed content-free projections,
- direct input-side node ordering.

Current limitation:

- most node results do not yet control routing, retry, fallback, or recovery.

## Phase 5-A: pure non-stream RelayCTX Unpack — complete

Implemented:

- pure parser in `relaylm/relayctx_unpack.py`,
- fixed `relayctx_working_update.v0`,
- one trailing supported candidate envelope,
- bounded/fail-closed parsing,
- safe visible-prefix preservation,
- detached candidate storage,
- no CTX/MEM/SOUL persistence.

## Phase 5-B: gated non-stream Unpack — complete

Implemented:

- enable/apply/dry-run/max-size gates,
- supported successful non-stream assistant-content mutation only,
- unrelated provider fields preserved,
- direct node-result recording,
- no streaming mutation or persistence.

## Phase 5-C: managed-route client authority — in progress

Phase 5-C separates correctness from instruction-cache optimization.

### Phase 5-C1: client-message canonicalization — complete as dry-run

Implemented:

- managed-route content-free inspection,
- latest valid user-turn detection,
- text/multimodal shape classification,
- prior-history and instruction counts,
- active tool-transaction preservation block,
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
  + missing / blocked / non-applied result
  -> block backend forward
```

This slice does not implement:

- instruction-bearing managed apply,
- cache-hit RelaySCN injection,
- cache-miss low-trust instruction evidence,
- typed instruction parse,
- cache write,
- Stream Unpack.

### Phase 5-C2: instruction identity and read-only cache lookup — complete

Implemented:

- current instruction extraction,
- request-local identity/fingerprint preparation,
- route/character-scoped cache identity,
- bounded file-backed read-only lookup,
- content-free hit/miss/blocked evidence.

Not implemented:

- cached scene-state injection,
- cache entry write.

### Phase 5-C3: history-exclusion preflight — complete

Implemented:

- typed request-local preflight,
- current-user message candidate,
- history exclusion counts,
- pass-through exemption,
- active transaction block,
- instruction-resolution mode classification,
- ready/pending/blocked/skipped outcomes,
- content-free projection.

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

### 5-D1 CJK-aware token estimation

- replace the single `chars_per_token=4` assumption with deterministic bounded estimation,
- distinguish CJK-heavy and ASCII-heavy input,
- use conservative rounding,
- cover Japanese, ASCII, mixed text, emoji, Markdown, and code.

### 5-D2 lazy RelayRUN recovery detail

- keep a minimal ordinary-path summary,
- build full recovery detail only when configuration, node state, persistence, or full diagnostics requires it,
- preserve current fail-closed and content-free contracts,
- avoid visible behavior changes.

## Phase 5.5: Stream Unpack and segmentation — planned

Planned:

- stream parser with non-stream-equivalent marker rules,
- early safe visible chunk forwarding,
- trailing marker buffering,
- incomplete candidate blocking,
- cancellation/disconnect handling,
- duplicate-emission prevention,
- TTS-safe segmentation,
- content-free stream diagnostics.

RelayLM owns safe visible segment boundaries. External TTS and avatar engines remain external consumers.

## External realtime validation — planned

Validate:

```text
frontend
  -> RelayLM stream
  -> backend
  -> safe visible segments
  -> external TTS/avatar adapters
```

Cover first-speech latency, marker non-leakage, ordering, cancellation, and fallback behavior.

## Phase 6: node-result routing — planned

- promote selected node outcomes into continue/skip/short-circuit/fallback/blocked routes,
- implement safe quick-clarification apply,
- let RelayRUN consume results incrementally,
- preserve idempotency and stream failure rules.

## Phase 7: RelayREF — planned

- diagnostics-only post-generation checks,
- empty/invalid output detection,
- internal marker and diagnostic leakage detection,
- bounded scene/policy mismatch observations,
- no default regeneration or output replacement.

## Phase 8: output-side RelaySCN — planned

- next-turn transition evaluation,
- recovery and persistence-block observations,
- immediate blocking only for invalid/leaking/safety-critical cases,
- no general output rewriting.

## Phase 9: RelayRUN cross-cutting orchestration — planned

- per-node lifecycle status,
- persistent checkpoints and resume metadata,
- timeout/retry/skip/fallback policy,
- stream partial-output state,
- waiting-user contracts,
- duplicate prevention,
- normal output-pipeline routing for visible recovery text.

## Phase 10: RelaySLP separation — planned

- governed source evidence,
- deferred memory/SOUL candidate extraction,
- safety and scope classification,
- hold/reject/proposal states,
- gated persistence,
- no direct normal-turn MEM or SOUL mutation.

## Deferred optimization track

### Phase 5-C4b cache-hit RelaySCN projection

- validate exact schema/policy/route/character/version scope,
- inject only allowlisted scene-state projection,
- never inject raw cached instructions or opaque bodies,
- keep visible response independent from cache availability.

### Phase 5-C5 typed instruction artifact and cache write

- use a separate schema such as `client_instruction_parse.v1`,
- accept only allowlisted scene role/context/constraint fields,
- block runtime, tool, safety, persistence, and persona overrides,
- keep durable persona content proposal-only,
- write only after schema/policy/scope/provenance validation,
- never mutate RelaySOUL from normal chat.

## Immediate next boundary

The next implementation slice is the instruction-bearing remainder of Phase 5-C4a.

Keep it separate from cache optimization, Stream Unpack, RelayREF, RelaySOUL work, and full RelayRUN routing.
