# RelayLM Project Status

Last reviewed: 2026-06-16 JST

## Purpose and authority

This page is the concise current-state view for developers and reviewers.

It answers:

- what works now,
- what exists only as dry-run, preflight, read-only, or default-off behavior,
- what is not implemented yet,
- and what implementation boundary comes next.

This page is **not** an independent source of truth.

When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) is authoritative for component ownership and canonical pipeline order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) is authoritative for phase status, implementation detail, and sequencing.
3. Dedicated module and contract documents are authoritative for schemas and bounded behavior.
4. `docs/mvp/` documents are historical implementation snapshots.

## Current position

```text
Current phase: Phase 5-C — in progress
Immediate next boundary: Phase 5-C4a managed-route history-exclusion apply
```

Completed foundations:

- OpenAI-compatible proxy and route handling,
- `PipelineContext` request-local coordination,
- main RelayCTX Repack separation,
- RelayINT-facing reference-repair boundary,
- ordered `PipelineNodeResult` scaffold,
- pure non-stream RelayCTX Unpack contract,
- gated non-stream runtime Unpack,
- managed-route client-message canonicalization dry-run,
- runtime-private client-instruction identity,
- read-only instruction-cache lookup,
- diagnostics-only client-history exclusion preflight.

Not yet enabled:

- managed-route client-history exclusion apply,
- current-turn-only managed message replacement,
- cache-hit RelaySCN state injection,
- typed client-instruction response artifact parsing,
- instruction-cache write,
- streaming RelayCTX Unpack and TTS-safe output segmentation,
- output-side RelayREF runtime observer,
- output-side RelaySCN runtime transition handling,
- cross-cutting per-node RelayRUN orchestration,
- asynchronous RelaySLP persistence apply.

## Revised near-term sequence

The near-term roadmap now separates the client-authority correctness boundary from the instruction-cache optimization track.

```text
Phase 5-C4a
  managed-route history-exclusion apply
  + current-turn preservation
  + optional escaped low-trust instruction evidence

Phase 5-D
  CJK-aware token estimation
  + lazy RelayRUN recovery-detail construction

Phase 5.5
  Stream Unpack
  + internal-marker-safe streaming
  + TTS-safe output segmentation

Deferred optimization track
  Phase 5-C4b cache-hit RelaySCN projection
  Phase 5-C5 typed instruction artifact and cache write
```

Phase 5-C4b and Phase 5-C5 remain valid long-term design work, but they no longer block Phase 5.5.

## Phase 5-C progress

| Boundary | Status | Current effect |
|---|---|---|
| 5-C1 client-message canonicalization | Complete as dry-run | Content-free inspection only; no payload mutation |
| 5-C2 instruction extraction and identity | Complete as runtime-private boundary | Request-local identity preparation; no visible effect |
| 5-C2 read-only cache lookup | Complete as read-only boundary | Hit/miss/blocked evidence only; no state injection |
| 5-C3 history-exclusion preflight | Complete as diagnostics-only preflight | Proves readiness; `payload_mutation_applied=false` |
| 5-C4a managed-route history-exclusion apply | Next | Will replace managed-route client history with validated current-turn and RelayLM-owned context |
| 5-C4b cache-hit RelaySCN projection | Deferred | Optional optimization; no longer gates Phase 5.5 |
| 5-C5 typed instruction artifact and cache write | Deferred | Optional optimization; no longer gates Phase 5.5 |

## Component status

The status terms below are intentionally more precise than “implemented” or “not implemented.”

| Component or boundary | Contract | Runtime wiring | Apply or user-visible effect | Default posture |
|---|---:|---:|---:|---|
| OpenAI-compatible proxy / adapters | Yes | Yes | Yes | Active |
| Route resolution and mode selection | Yes | Yes | Yes | Active |
| `PipelineContext` | Yes | Yes | Yes | Active |
| RelayCTX Repack | Yes | Yes | Yes | Route/config dependent |
| RelayMEM retrieval and CTX injection | Yes | Yes | Gated | Default-safe / bounded |
| RelayCTX short-term injection | Yes | Yes | Gated | Default-off apply |
| RelayINT reference repair | Yes | Yes | Diagnostic/decision support | Compatibility aliases remain |
| RelayINT Fast Path | Yes | Yes | Diagnostics only | Default-off |
| RelayINT quick clarification | Yes | Preflight/apply plan | No completed short-circuit route | Default-off |
| `PipelineNodeResult` | Yes | Yes | Mostly diagnostics only | Active collection |
| RelayCTX Unpack non-stream | Yes | Yes | Gated visible-content separation | Default-off apply |
| RelayCTX Unpack streaming | Design | No | No | Planned |
| Client-message canonicalization | Yes | Yes | No | Dry-run/default-off |
| Client-instruction identity | Yes | Yes | No | Runtime-private |
| Instruction-cache lookup | Yes | Yes | Read-only | Default-off |
| Client-history exclusion | Yes | Yes | Preflight only | Default-off |
| Runtime Compile Gate | Contracts/design | Partial decision artifacts | No unified apply gate | In progress |
| RelayREF output observer | Design | No dedicated runtime stage | No | Planned |
| Output-side RelaySCN | Design/contracts | Partial recovery artifacts | No complete stage | Planned |
| RelayRUN | Yes | Request-level artifacts/checkpoints | Partial orchestration | Recovery detail currently eager; lazy construction planned |
| RelaySLP | Design/contracts | Partial dry-run/preflight foundations | No complete asynchronous apply path | Planned |
| RelaySOUL apply/persistence | Contracts and gates | Dry-run/preflight/gate foundations | Explicit gated operations only | Runtime expansion frozen until the core output path is stable |

## Usable runtime paths

### Standard local path

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

This remains the primary MVP path.

### Optional frontend path

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

Open-LLM-VTuber remains an optional integration. RelayLM does not own its UI, ASR, TTS, or avatar runtime.

RelayLM does own the safety boundary that separates user-visible stream segments from internal control data before an external TTS or avatar adapter consumes them.

### Current behavioral baseline

- `pass_through` remains the compatibility baseline.
- Managed modes can compile and repack RelayLM-owned context.
- Non-stream RelayCTX Unpack exists behind safe gates.
- Streaming remains primarily backend-forwarding behavior; internal-marker-safe Stream Unpack is not implemented.
- Client-message canonicalization and history exclusion do not yet mutate managed-route payloads.
- Instruction-cache lookup does not yet inject cached scene state or write new entries.
- Token budgeting still uses a single character-ratio heuristic that is not sufficiently conservative for Japanese/CJK text.
- RelayRUN recovery features are default-off, but detailed recovery artifacts are still constructed eagerly on the request path.

## Immediate next implementation slice

Phase 5-C4a must remain a narrow correctness boundary:

```text
validated client-message canonicalization
+ history-exclusion preflight
  -> dedicated managed-route apply helper
  -> current-turn-only client message preservation
  -> RelayLM-owned context preservation
  -> at most one escaped low-trust current-instruction evidence block when required
  -> PipelineContext payload replacement reason
  -> content-free node result and smoke coverage
```

It must preserve:

- `pass_through` behavior,
- active tool transactions,
- current multimodal user parts,
- structured-output and provider compatibility,
- fail-closed behavior,
- content-free diagnostics.

It must not include:

- cache-hit RelaySCN projection,
- typed client-instruction output parsing,
- instruction-cache write,
- RelaySOUL mutation,
- Stream Unpack,
- RelayREF implementation,
- full RelayRUN route-table promotion.

## Phase 5-D pre-stream hardening

After Phase 5-C4a and before Phase 5.5 runtime apply work:

1. Replace the single `chars_per_token=4` assumption with a bounded CJK-aware token-estimation policy and mixed Japanese/ASCII/code smoke coverage.
2. Keep the minimal RelayRUN checkpoint summary on the normal path, but construct the detailed recovery chain only when recovery-related configuration, a recovery-relevant node result, checkpoint persistence, or explicit full trace diagnostics requires it.
3. Preserve all existing fail-closed and content-free contracts while reducing normal-path allocation and serialization work.

## Main remaining roadmap

1. Phase 5-C4a — managed-route history-exclusion apply.
2. Phase 5-D — CJK-aware token estimation and RelayRUN recovery-detail lazy construction.
3. Phase 5.5 — Stream Unpack and TTS-safe output segmentation.
4. External end-to-end validation — frontend -> RelayLM stream -> backend -> safe visible segments -> external TTS/avatar stack.
5. Phase 6 — promote selected node results into explicit routing/apply behavior.
6. Phase 7 — lightweight output-side RelayREF observer.
7. Phase 8 — Output-side RelaySCN next-turn state handling.
8. Phase 9 — cross-cutting RelayRUN per-node checkpoint/orchestration layer.
9. Phase 10 — asynchronous RelaySLP separation and persistence path.
10. Deferred optimization track — Phase 5-C4b cache-hit projection and Phase 5-C5 typed parse/cache write after the core streaming path is validated.

## Where to read next

- Current implementation detail and phase sequencing: [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- Stable ownership and canonical order: [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md)
- Runtime reliability and fallback requirements: [Runtime Operational Requirements](architecture/runtime_operational_requirements.md)
- Product and AI-character experience priorities: [AI Character Product Principles](architecture/ai_character_product_principles.md)
- Historical milestone evidence: [MVP summaries and milestone notes](mvp/README.md)
- Validation procedures: [Smoke and validation docs](smoke/README.md)

## Update rule

Update this page when any of these changes:

- current phase or immediate next boundary,
- a component moves from design to runtime wiring,
- a boundary moves from dry-run/preflight/read-only to apply,
- a default-off behavior becomes default-on,
- supported request, response, streaming, or persistence behavior changes materially.

Do not update it for internal refactoring, comment-only changes, or additional smoke coverage that does not change the current capability boundary.
