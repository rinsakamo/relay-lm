# RelayLM Project Status

Last reviewed: 2026-06-15 JST

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
Immediate next boundary: Phase 5-C4 managed-route apply
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

- managed-route client-message replacement,
- cache-hit RelaySCN state injection,
- cache-miss first-pass instruction-evidence apply,
- typed client-instruction response artifact parsing,
- instruction-cache write,
- streaming RelayCTX Unpack and TTS-safe output segmentation,
- output-side RelayREF runtime observer,
- output-side RelaySCN runtime transition handling,
- cross-cutting per-node RelayRUN orchestration,
- asynchronous RelaySLP persistence apply.

## Phase 5-C progress

| Boundary | Status | Current effect |
|---|---|---|
| 5-C1 client-message canonicalization | Complete as dry-run | Content-free inspection only; no payload mutation |
| 5-C2 instruction extraction and identity | Complete as runtime-private boundary | Request-local identity preparation; no visible effect |
| 5-C2 read-only cache lookup | Complete as read-only boundary | Hit/miss/blocked evidence only; no state injection |
| 5-C3 history-exclusion preflight | Complete as diagnostics-only preflight | Proves readiness; `payload_mutation_applied=false` |
| 5-C4 managed-route apply | Next | Will replace managed-route messages using validated current-turn and instruction state |
| 5-C5 typed instruction artifact and cache write | Planned | Will validate first-pass output and independently gate cache writes |

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
| RelayRUN | Yes | Request-level artifacts/checkpoints | Partial orchestration | Cross-cutting node control planned |
| RelaySLP | Design/contracts | Partial dry-run/preflight foundations | No complete asynchronous apply path | Planned |
| RelaySOUL apply/persistence | Contracts and gates | Dry-run/preflight/gate foundations | Explicit gated operations only | Never silent from normal chat |

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

### Current behavioral baseline

- `pass_through` remains the compatibility baseline.
- Managed modes can compile and repack RelayLM-owned context.
- Non-stream RelayCTX Unpack exists behind safe gates.
- Streaming remains primarily backend-forwarding behavior; internal-marker-safe Stream Unpack is not implemented.
- Client-message canonicalization and history exclusion do not yet mutate managed-route payloads.
- Instruction-cache lookup does not yet inject cached scene state or write new entries.

## Immediate next implementation slice

Phase 5-C4 should remain a narrow apply boundary:

```text
validated client-message canonicalization
+ runtime-private instruction identity
+ read-only cache lookup
+ history-exclusion preflight
  -> dedicated managed-route apply helper
  -> current-turn-only client message preservation
  -> validated cache-hit scene projection
     OR one escaped cache-miss instruction-evidence block
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

- instruction-cache write,
- RelaySOUL mutation,
- Stream Unpack,
- RelayREF implementation,
- full RelayRUN route-table promotion.

## Main remaining roadmap

After Phase 5-C:

1. Phase 5.5 — Stream Unpack and TTS-safe output segmentation.
2. Phase 6 — promote selected node results into explicit routing/apply behavior.
3. Phase 7 — lightweight output-side RelayREF observer.
4. Phase 8 — Output-side RelaySCN next-turn state handling.
5. Phase 9 — cross-cutting RelayRUN per-node checkpoint/orchestration layer.
6. Phase 10 — asynchronous RelaySLP separation and persistence path.

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
