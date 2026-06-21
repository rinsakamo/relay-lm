---
relaylm_doc_type: implementation_plan
relaylm_authority: implementation_status_and_phase_sequencing
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - phase lands
  - sequencing changes
  - target-only schema gains producer consumer apply skip block contract projection and smoke coverage
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical MVP authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - current_target_migration_guide.md
  - phase5_5_stream_unpack_bounded_slice.md
  - soul_lab_runtime_mvp.md
---
# RelayLM Pipeline Implementation Plan

## Purpose

This document owns implementation status, phase sequencing, and dependency boundaries. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

## Status legend

- **complete**: bounded contract, runtime wiring, and smoke coverage exist.
- **mostly complete**: the main boundary exists with bounded follow-up remaining.
- **planned**: design exists without a complete runtime producer/consumer/apply path.
- **deferred**: intentionally not a gate for the active boundary.

## Current position

```text
Phase 5-C managed-route correctness: complete
Phase 5-D1 CJK-aware token estimation: complete
Phase 5-D2 lazy RelayRUN recovery detail: complete
Phase 5.5 Stream Unpack / TTS handoff preparation: complete for RelayLM Core

Completed bounded slices:
  Phase 1 PipelineContext/app stabilization
  Phase 2 documentation consolidation
  Phase 3 RelayCTX Repack separation
  Phase 4 RelayINT compatibility boundary
  Phase 4.5 PipelineNodeResult
  Phase 5-A pure non-stream RelayCTX Unpack
  Phase 5-B gated non-stream RelayCTX Unpack
  Phase 5-C1 through C3 authority foundations
  Phase 5-C1a no-instruction managed apply
  Phase 5-C4a instruction-bearing managed apply
  Phase 5-C4b cache-hit RelaySCN projection
  Phase 5-C5a typed parse/cache-write preflight
  Phase 5-C5b gated cache writer helper
  Phase 5-C5c runtime cache-writer boundary
  Phase 5-D1 CJK-aware conservative token estimation
  Phase 5-D2a lazy RelayRUN recovery-detail helper
  Phase 5-D2b lazy RelayRUN recovery-detail runtime wiring
  Phase 5.5-A stream sentinel buffer dry-run
  Phase 5.5-B1 stream suppression gate helper
  Phase 5.5-B2 request-runtime SSE suppression wiring
  Phase 5.5-C0 TTS segmentation helper
  Phase 5.5-C1 TTS adapter handoff contract
  Phase 5.5-C2 runtime TTS adapter handoff wiring
  Phase 5.5-C3 TTS adapter transport contract
  Phase 5.5-C4 runtime TTS adapter transport-envelope construction

Next RelayLM Core candidate:
  Phase 6 asynchronous RelaySLP

Later product/runtime candidate:
  SOUL Lab Runtime MVP adapter bridge and TTS/audio/Live2D execution
```

Phase 5.5 is closed for RelayLM Core. It preserves default backend SSE forwarding while adding safe stream-level visible/internal separation, TTS-safe segmentation hints, runtime-private adapter handoff plans, and runtime-private adapter-facing transport envelopes.

Phase 5.5 does **not** own concrete adapter delivery, TTS execution, audio generation, audio queueing, Live2D/avatar control, lip-sync, or runtime mapping UI. Those execution concerns are explicitly deferred to [SOUL Lab Runtime MVP](soul_lab_runtime_mvp.md).

## Current caveats

- Managed apply remains default-off and dry-run-only by default.
- Current profile compilation still precedes normalized target SCN/INT/Retrieval handoffs.
- Complete Runtime Compile Gate v1 route-authority/fallback/source taxonomy is not implemented.
- Active tool transactions remain blocked because minimum-chain reconstruction is absent.
- Instruction-cache lookup and RelaySCN projection are read-only.
- Phase 5-C5c wires a trusted in-process typed parse source to the gated writer, but response/control-envelope extraction, frontend metadata trust, and parser-versioned lookup/write compatibility remain absent.
- RelayCTX Unpack is non-stream only outside the bounded Phase 5.5 stream safety path.
- Phase 5.5 emits stream-final content-free metadata only; adapter delivery and TTS/audio/avatar execution remain outside RelayLM Core.
- New RelaySOUL execution-gate design documents should still be avoided unless they directly unblock a current runtime safety issue or are part of the later SOUL Lab runtime adapter boundary.
- Token estimation is deterministic and CJK-aware but remains tokenizer-free and model-agnostic rather than exact.
- RelayRUN lazy recovery detail is wired into the request-runtime checkpoint builder, but cross-cutting per-node orchestration remains later work.
- RelayREF output observation, RelaySLP persistence, and RelaySOUL actual apply remain later work.

## Completed implementation groups

### Phase 1: PipelineContext/app — mostly complete

Implemented request-local original/forwarded payload separation, explicit mutation reasons, runtime-private candidates, ordered node results, and grouped diagnostics. New semantic ownership should remain outside `app.py`.

### Phase 2: documentation consolidation — substantially complete

Current, compatibility, target, migration, and historical material are separated. Documentation maintenance follows runtime changes.

### Phase 3: RelayCTX Repack — mostly complete

Main backend-bound mutation phases are grouped under RelayCTX Repack, including RelayMEM/CTX injection and token-budget application. No new prompt mutation may bypass owned Repack or managed-authority gates.

### Phase 4: RelayINT compatibility boundary — complete

Input-side reference repair is exposed through RelayINT-facing wrappers. Historical RelayREF names remain only where compatibility requires them.

### Phase 4.5: PipelineNodeResult — complete

Frozen request-local node results, deterministic ordering, and typed content-free projections are implemented. Universal routing/retry control remains later work.

### Phase 5-A and 5-B: non-stream RelayCTX Unpack — complete

The pure parser and gated runtime boundary support one bounded trailing update envelope, preserve ordinary visible output, fail closed on malformed candidates, and do not persist CTX/MEM/SOUL/SLP state.

### Phase 5-C: managed-route client authority — correctness complete

Phase 5-C provides client-message canonicalization, instruction identity, read-only cache lookup, history-exclusion preflight, no-instruction and instruction-bearing managed apply, cache-hit RelaySCN projection, typed parse/cache-write preflight, gated cache writer helper, and request-local cache-writer runtime wiring.

The correctness boundary is complete. Response/control-envelope extraction, frontend metadata trust, RelaySCN policy application, parser-versioned lookup/write compatibility, and user-visible response mutation remain outside the completed boundary.

### Phase 5-D: pre-stream hardening — complete through D2

Phase 5-D1 implements tokenizer-free deterministic CJK-aware conservative token estimation. Phase 5-D2 implements lazy RelayRUN recovery-detail helper and request-runtime wiring.

### Phase 5.5: Stream Unpack / TTS handoff preparation — complete for RelayLM Core

See [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md).

Completed:

1. **Phase 5.5-A: stream sentinel buffer dry-run** — pure/dry-run stream buffer state, sentinel detection across chunk boundaries, content-free diagnostics, unchanged emitted chunks, direct smoke, and dedicated CI workflow.
2. **Phase 5.5-B1: stream suppression gate helper** — explicit enabled/dry-run gate, safe visible prefix preservation, complete/split internal sentinel suppression, terminal partial sentinel blocking, invalid chunk fail-closed behavior, content-free node result, and direct smoke coverage.
3. **Phase 5.5-B2: request-runtime SSE suppression wiring** — gated wrapping of runtime stream bytes, unchanged default forwarding, dry-run pass-through diagnostics, apply-mode internal suppression, partial/backend failure summary, and duplicate replay prevention.
4. **Phase 5.5-C0: TTS segmentation helper** — explicit enabled/dry-run gate, content-free character-range hints, sentence/newline/length/stream-end boundaries, internal sentinel blocking, invalid chunk fail-closed behavior, and direct smoke coverage.
5. **Phase 5.5-C1: TTS adapter handoff contract** — explicit enabled/dry-run gate, runtime-private downstream handoff plan, candidate/emitted count separation, conservative C0 status propagation, content-free node result, and direct smoke coverage.
6. **Phase 5.5-C2: runtime TTS adapter handoff wiring** — default-off pass-through observer for B2 safe visible output, C0/C1 runtime node result recording, no TTS/audio/avatar execution, and direct smoke coverage.
7. **Phase 5.5-C3: TTS adapter transport contract** — helper-only adapter-facing transport envelope construction from C1 handoff plans, content-free node result, no adapter delivery, no TTS/audio/avatar execution, and direct smoke coverage.
8. **Phase 5.5-C4: runtime TTS transport-envelope construction** — default-off runtime construction of C3 envelopes after C2 stream-final handoff planning, C0/C1/C3 stream-final trace projection, no adapter delivery, no TTS/audio/avatar execution, and direct smoke coverage.

C4b, C5, and RelaySOUL execution gates are not prerequisites for Phase 6 asynchronous RelaySLP or later SOUL Lab Runtime MVP work.

## Phase 6: asynchronous RelaySLP — planned

Deferred candidate processing, gated MEM page/index/log updates, idempotency, retry policy, and persistence safety classification belong here. RelaySLP must not directly mutate SOUL.

Phase 6 should preserve the Phase 5.5 boundary: stream/TTS handoff metadata may inform later runtime behavior, but TTS execution, audio generation, Live2D/avatar control, and transport delivery remain SOUL Lab Runtime MVP concerns.

## SOUL Lab Runtime MVP relationship — planned later

SOUL Lab Runtime MVP owns the concrete runtime execution layer after RelayLM Core produces safe output and runtime-private metadata. It owns:

- concrete TTS adapter mapping,
- TTS execution,
- audio queueing,
- caption/voice timing coordination,
- Live2D/avatar expression mapping,
- avatar motion scheduling,
- lip-sync timing when supported,
- runtime preview, calibration, mapping UI, and adapter failure handling.

RelayLM Core must not directly call TTS engines, Live2D runtimes, avatar motion systems, audio playback queues, or OBS/streaming integrations.

## Update rule

Update this plan whenever a phase lands, sequencing changes, or a target-only schema gains an implemented producer, consumer, apply/skip/block contract, content-free projection, and smoke coverage.
