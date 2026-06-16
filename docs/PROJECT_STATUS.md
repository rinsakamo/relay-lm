# RelayLM Project Status

Last reviewed: 2026-06-16 JST

## Purpose and authority

This page is the concise current-state view.

Use:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) for component ownership and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) for phase status and sequencing.
3. Dedicated contracts for implemented schemas and bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) for interpretation of compatibility and target material.

## Current position

```text
Current phase: Phase 5-C — in progress

Latest completed bounded slice:
  no-instruction managed-route history exclusion apply
  + request-local runtime wiring
  + backend-forward gate

Next boundary:
  complete Phase 5-C4a for instruction-bearing managed requests
```

The new apply slice is narrower than the complete managed-route authority target.

## Completed foundations

- OpenAI-compatible routing and backend forwarding,
- `PipelineContext` and ordered `PipelineNodeResult` collection,
- main RelayCTX Repack separation,
- RelayINT-facing reference repair,
- pure and gated non-stream RelayCTX Unpack,
- client-message canonicalization dry-run,
- runtime-private client-instruction identity,
- read-only instruction-cache lookup,
- client-history exclusion preflight,
- `client_history_exclusion_apply.v0`,
- no-instruction apply runtime wiring,
- backend-forward blocking for an explicitly requested actual apply that lacks an applied result.

## Current no-instruction apply slice

Current producer and schema:

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
- enabled with dry-run-only: request-local candidate only,
- enabled with actual apply on a managed route: mutate only on an exact `applied` result,
- explicit actual apply without an applicable result: backend forwarding is blocked,
- `pass_through`: exempt and remains client-authority delegated.

The rebuilt payload is request-local and content-bearing. Persisted projections contain only typed metadata.

## Not yet complete

- instruction-bearing managed-route history exclusion,
- bounded low-trust current-instruction evidence apply,
- cache-hit RelaySCN projection,
- typed client-instruction response parsing,
- instruction-cache write,
- complete target Runtime Compile Gate taxonomy and managed fallback builder,
- Stream Unpack and TTS-safe segmentation,
- output-side RelayREF,
- complete output-side RelaySCN runtime handling,
- cross-cutting per-node RelayRUN orchestration,
- asynchronous RelaySLP persistence apply,
- actual RelaySOUL apply, rollback, and persistence execution.

## Phase 5-C progress

| Boundary | Status | Current effect |
|---|---|---|
| 5-C1 canonicalization | Complete as dry-run | Inspection only |
| 5-C1a no-instruction apply | Complete as bounded default-off slice | Candidate in dry-run; current-turn-only payload in actual apply |
| 5-C2 instruction identity | Complete as runtime-private | No user-visible effect |
| 5-C2 cache lookup | Complete as read-only | No state injection or write |
| 5-C3 history-exclusion preflight | Complete | Supplies request-local readiness and current-user candidate |
| 5-C4a broader correctness path | In progress | Instruction-bearing path remains absent |
| 5-C4b cache-hit projection | Deferred | Optimization |
| 5-C5 typed parse/cache write | Deferred | Optimization |

The late `5-C1a` label identifies the bounded no-instruction slice. It does not replace the broader `5-C4a` completion criteria.

## Component status

| Boundary | Current status | Default posture |
|---|---|---|
| OpenAI-compatible proxy | Active | Active |
| RelayCTX Repack | Runtime wired | Route/config dependent |
| RelayMEM Retrieval and injection | Runtime wired, gated | Default-safe / bounded |
| RelayINT reference repair | Runtime wired | Compatibility aliases remain |
| RelayINT Fast Path | Diagnostics | Default-off |
| RelayCTX Unpack non-stream | Runtime wired, gated | Default-off apply |
| RelayCTX Unpack streaming | Design only | Planned |
| Client canonicalization | Dry-run | Default-off |
| Client-history preflight | Runtime-private preflight | Default-off |
| Client-history apply v0 | No-instruction apply | Default-off; dry-run by default |
| Runtime Compile Gate | Partial current decision plus target contracts | In progress |
| RelayREF | Design only | Planned |
| Output-side RelaySCN | Partial artifacts only | Planned |
| RelayRUN | Request-level artifacts and partial orchestration | Most features default-off |
| RelaySLP | Dry-run/preflight foundations | Planned |
| RelaySOUL execution | Dry-run/preflight foundations | Actual mutation disabled |

## Runtime paths

Primary local path:

```text
OpenWebUI -> RelayLM -> LM Studio
```

Optional path:

```text
Open-LLM-VTuber -> RelayLM -> OpenAI-compatible backend
```

Open-LLM-VTuber remains optional. RelayLM does not own frontend UI, ASR, TTS execution, or avatar execution.

## Immediate next boundary

Complete instruction-bearing Phase 5-C4a without combining deferred cache optimization:

```text
validated current instruction evidence
  -> escaped bounded low-trust block when required
  -> validated current user content
  -> RelayLM-owned managed payload
  -> explicit PipelineContext replacement
```

The path must preserve `pass_through`, compatibility-sensitive transactions, content-free projections, and the rule that a managed failure does not restore prior client history.

## Near-term sequence

1. Complete instruction-bearing Phase 5-C4a.
2. Phase 5-D — CJK-aware token estimation and lazy RelayRUN recovery detail.
3. Phase 5.5 — Stream Unpack and TTS-safe segmentation.
4. External realtime validation.
5. Later routing, RelayREF, output-side RelaySCN, RelayRUN, and RelaySLP phases.

## Where to read next

- [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Client History Exclusion Apply Forward Gate](architecture/client_history_exclusion_apply_forward_gate.md)
- [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md)
- [Smoke and validation docs](smoke/README.md)
