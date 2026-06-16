# RelayLM Project Status

Last reviewed: 2026-06-17 JST

## Purpose and authority

This page is the concise current-state view for developers and reviewers.

It answers:

- what works now,
- what exists only as dry-run, preflight, read-only, runtime-private, or default-off behavior,
- what is not implemented yet,
- and what implementation boundary comes next.

This page is a summary view rather than an independent source of truth.

When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) is authoritative for component ownership and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) is authoritative for phase status, implementation detail, dependencies, and sequencing.
3. Dedicated module and contract documents are authoritative for exact current schemas and bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) defines how compatibility and target material must be interpreted.
5. `docs/mvp/` documents are historical implementation snapshots.

## Current position

```text
Current phase: Phase 5-C — in progress

Latest completed bounded slice:
  Phase 5-C1a no-instruction managed-route history exclusion apply
  + request-local runtime wiring
  + backend-forward gate

Immediate next boundary:
  complete Phase 5-C4a for instruction-bearing managed requests
```

The 5-C1a slice is narrower than the complete managed-route authority target. It does not make Phase 5-C complete.

## Completed foundations

- OpenAI-compatible proxy, route handling, and backend forwarding,
- `PipelineContext` request-local coordination,
- ordered `PipelineNodeResult` collection,
- main RelayCTX Repack separation,
- RelayINT-facing reference-repair boundary,
- pure non-stream RelayCTX Unpack contract,
- gated non-stream runtime Unpack,
- managed-route client-message canonicalization dry-run,
- runtime-private client-instruction identity,
- read-only instruction-cache lookup,
- client-history exclusion preflight,
- `client_history_exclusion_apply.v0`,
- no-instruction apply runtime wiring,
- backend-forward blocking for explicitly requested actual apply without an exact applied result.

## Current no-instruction apply slice

Current producers and schema:

```text
relaylm.client_history_exclusion_apply.build_client_history_exclusion_apply
relaylm.client_history_exclusion_apply_runtime.run_client_history_exclusion_apply_runtime
client_history_exclusion_apply.v0
```

Current defaults:

```text
client_history_exclusion_apply_enabled = false
client_history_exclusion_apply_dry_run_only = true
```

Supported shape:

```text
compiled memory_light payload
  + ready history-exclusion preflight
  + no client system/developer messages
  -> one RelayLM-owned compiled prefix message
  -> validated current user message
```

Behavior:

- disabled: no result and no mutation,
- enabled with dry-run-only: request-local payload candidate only,
- enabled with actual apply on a managed route: mutate only on an exact `applied` result,
- explicit actual apply with a missing, blocked, skipped, ready-only, or otherwise non-applied result: block backend forwarding,
- runtime exception: convert to a bounded blocked result,
- explicit `pass_through`: exempt and remains client-authority delegated.

The rebuilt payload is request-local and content-bearing. Persisted projections contain only typed metadata. The current schema has no separate `failed` status.

## Current Compile surfaces

Current compilation has two implemented surfaces:

1. `relaylm.compile_gate.CompileApplyDecision` with `should_apply`, `mode_applied`, `profile_compile_ready`, and `reason`.
2. The content-free `mvp-ctx-apply-0` diagnostics artifact built by `relaylm.diagnostics.build_compile_decision_dry_run`, currently using `COMPILE_APPLY` or `COMPILE_DRY_RUN` on the request path.

The complete v1 route-authority, forwarded-payload-source, managed fallback, `COMPILE_FALLBACK`, and `BLOCKED` taxonomy remains target work.

## Not yet complete

- instruction-bearing managed-route history exclusion,
- bounded low-trust current-instruction evidence apply,
- cache-hit RelaySCN projection,
- typed client-instruction response parsing,
- instruction-cache write,
- complete target Runtime Compile Gate taxonomy and managed fallback builder,
- Stream Unpack and TTS-safe output segmentation,
- output-side RelayREF runtime observer,
- complete output-side RelaySCN runtime handling,
- cross-cutting per-node RelayRUN orchestration,
- asynchronous RelaySLP persistence apply,
- actual RelaySOUL apply, rollback, and persistence execution.

## Phase 5-C progress

| Boundary | Status | Current effect |
|---|---|---|
| 5-C1 client-message canonicalization | Complete as dry-run | Content-free inspection only; no payload mutation |
| 5-C1a no-instruction apply | Complete as bounded default-off slice | Candidate in dry-run; current-turn-only managed payload in actual apply |
| 5-C2 instruction extraction/identity | Complete as runtime-private boundary | Request-local identity; no visible effect |
| 5-C2 read-only cache lookup | Complete as read-only boundary | Hit/miss/blocked evidence only; no state injection or write |
| 5-C3 history-exclusion preflight | Complete | Request-local readiness and current-user candidate; no mutation |
| 5-C4a broader correctness path | In progress | Instruction-bearing path remains absent |
| 5-C4b cache-hit RelaySCN projection | Deferred | Optional optimization |
| 5-C5 typed parse/cache write | Deferred | Optional optimization |

The late `5-C1a` label identifies a bounded correctness slice. It does not replace the broader `5-C4a` completion criteria.

## Component status

The status terms below are intentionally more precise than “implemented” or “not implemented.”

| Component or boundary | Contract | Runtime wiring | Apply or user-visible effect | Default posture |
|---|---:|---:|---:|---|
| OpenAI-compatible proxy/adapters | Yes | Yes | Yes | Active |
| Route resolution and mode selection | Yes | Yes | Yes | Active |
| `PipelineContext` | Yes | Yes | Yes | Active |
| `PipelineNodeResult` | Yes | Yes | Mostly diagnostics | Active collection |
| Current profile compiler | Yes | Yes | `memory_light` apply-capable | Route dependent |
| Current compile diagnostics | `mvp-ctx-apply-0` | Yes | Diagnostics only | Active with request path |
| Target Runtime Compile Gate | Design/contracts | Partial current surfaces | No unified authority-aware gate | In progress |
| RelayCTX Repack | Yes | Yes | Yes | Route/config dependent |
| RelayMEM Retrieval and CTX injection | Yes | Yes | Gated | Default-safe/bounded |
| RelayCTX short-term source/extraction/assembly | Yes | Yes | Diagnostics/dry-run foundations | Default-off |
| RelayCTX short-term runtime injection | Yes | Yes | Gated apply helper | Default-off; dry-run by default |
| RelayINT reference repair | Yes | Yes | Diagnostic/decision support | Compatibility aliases remain |
| RelayINT Fast Path | Yes | Yes | Diagnostics only | Default-off |
| RelayINT quick clarification | Yes | Preflight/apply plan | No completed visible short-circuit route | Default-off |
| RelayCTX Unpack non-stream | Yes | Yes | Gated visible/internal separation | Default-off apply |
| RelayCTX Unpack streaming | Design | No | No | Planned |
| Client-message canonicalization | Yes | Yes | No | Dry-run/default-off |
| Client-instruction identity | Yes | Yes | No | Runtime-private |
| Instruction-cache lookup | Yes | Yes | Read-only | Default-off |
| Client-history exclusion preflight | Yes | Yes | No | Default-off |
| Client-history apply v0 | Yes | Yes | No-instruction apply | Default-off; dry-run by default |
| RelayREF output observer | Design | No dedicated runtime stage | No | Planned |
| Output-side RelaySCN | Design/contracts | Partial recovery artifacts | No complete stage | Planned |
| RelayRUN | Yes | Request-level artifacts/checkpoints | Partial orchestration | Recovery detail currently eager; most features default-off |
| RelaySLP | Design/contracts | Dry-run/preflight foundations | No asynchronous apply path | Planned |
| RelaySOUL governance | Contracts/gates | Dry-run/preflight foundations | No actual mutation/storage execution | Runtime expansion frozen during core-output work |

## Usable runtime paths

### Standard local path

```text
OpenWebUI
  -> RelayLM http://127.0.0.1:8090/v1
  -> LM Studio http://127.0.0.1:1234/v1
```

This remains the primary MVP path.

### Optional frontend path

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

Open-LLM-VTuber remains optional. RelayLM does not own its UI, ASR, TTS execution, or avatar execution.

RelayLM owns the target safety boundary that separates user-visible stream segments from internal control data before external TTS/avatar consumers. That Stream Unpack path is not yet implemented.

## Current behavioral baseline

- `pass_through` remains an explicit delegated compatibility route.
- Managed modes can compile and repack RelayLM-owned context.
- A managed failure must not restore excluded raw client history as fallback.
- Non-stream RelayCTX Unpack exists behind safe gates.
- Streaming remains primarily backend SSE forwarding; internal-marker-safe Stream Unpack is not implemented.
- The no-instruction history-exclusion slice can mutate managed payloads only when explicitly enabled in actual-apply mode.
- Instruction-cache lookup does not inject cached scene state or write new entries.
- Token budgeting still uses a single character-ratio heuristic that is not sufficiently conservative for Japanese/CJK-heavy text.
- RelayRUN recovery features are default-off, but detailed recovery artifacts are still constructed eagerly on the ordinary request path.
- RelaySOUL compatibility helpers may evaluate metadata, but actual apply, rollback, persistence, and file writes remain disabled.

## Immediate next implementation slice

Complete the instruction-bearing remainder of Phase 5-C4a without combining deferred cache optimization:

```text
validated client-message evidence
  + history-exclusion preflight
  -> dedicated managed-route apply helper
  -> current-turn-only client message preservation
  -> RelayLM-owned context preservation
  -> at most one escaped bounded low-trust current-instruction evidence block
  -> PipelineContext payload replacement reason
  -> content-free node result and smoke coverage
```

It must preserve:

- explicit `pass_through` behavior,
- active tool transactions,
- current multimodal user parts,
- structured-output and provider compatibility,
- fail-closed managed authority,
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

1. Replace the single `chars_per_token=4` assumption with a bounded CJK-aware token-estimation policy and Japanese/ASCII/mixed/code smoke coverage.
2. Keep the minimal RelayRUN request/run/node/backend summary on the ordinary path.
3. Construct detailed recovery artifacts only when recovery configuration, a recovery-relevant failed/blocked/waiting-user node, checkpoint persistence, or explicit full trace diagnostics requires them.
4. Preserve current fail-closed, content-free, and default-off contracts while reducing ordinary-path allocation and serialization.

## Main remaining roadmap

1. Complete Phase 5-C4a instruction-bearing managed apply.
2. Phase 5-D — CJK-aware token estimation and lazy RelayRUN recovery detail.
3. Phase 5.5 — Stream Unpack and TTS-safe output segmentation.
4. External realtime validation — frontend -> RelayLM stream -> backend -> safe visible segments -> external TTS/avatar stack.
5. Phase 6 — promote selected node results into explicit routing/apply behavior.
6. Phase 7 — lightweight output-side RelayREF observer.
7. Phase 8 — Output-side RelaySCN next-turn handling.
8. Phase 9 — cross-cutting RelayRUN per-node checkpoint/orchestration layer.
9. Phase 10 — asynchronous RelaySLP separation and persistence path.
10. Deferred optimization — Phase 5-C4b cache-hit projection and Phase 5-C5 typed parse/cache write after the core streaming path is validated.

## Where to read next

- [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Runtime Operational Requirements](architecture/runtime_operational_requirements.md)
- [Client History Exclusion Apply Forward Gate](architecture/client_history_exclusion_apply_forward_gate.md)
- [Runtime Compile Current / Target Boundary](contracts/runtime_compile_current_target.md)
- [Smoke and validation docs](smoke/README.md)

## Update rule

Update this page when any of these changes:

- current phase or immediate next boundary,
- a component moves from design to runtime wiring,
- a boundary moves from dry-run/preflight/read-only to apply,
- a default-off behavior becomes default-on,
- supported request, response, streaming, recovery, or persistence behavior changes materially,
- a current schema, producer, or consumer changes.

Do not update it for internal refactoring, comment-only changes, or additional smoke coverage that does not change the current capability boundary.
