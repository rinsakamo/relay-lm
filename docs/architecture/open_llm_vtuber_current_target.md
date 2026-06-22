# Open-LLM-VTuber Current / Target Boundary

## Current implemented

Open-LLM-VTuber is an optional OpenAI-compatible frontend path:

```text
Open-LLM-VTuber -> RelayLM -> OpenAI-compatible backend
```

Current behavior:

- ordinary streaming remains byte-compatible backend SSE forwarding by default,
- Phase 5.5-B2 can perform gated request-runtime internal-sentinel suppression when explicitly enabled,
- Phase 5.5-C0 through C4 can build TTS-safe segmentation hints, adapter-handoff plans, and adapter-facing transport envelopes from B2 safe visible output behind explicit default-off gates,
- `client_history_exclusion_apply.v0` supports bounded managed no-instruction requests,
- `client_history_exclusion_apply.v1` supports bounded instruction-bearing requests only when exact `client_instruction_source.v1` provenance is supplied,
- both history-exclusion apply paths remain default-off and dry-run-only by default,
- missing or invalid v1 provenance fails closed rather than restoring raw history or treating every system/developer message as current instruction evidence,
- non-stream RelayCTX Unpack and the Phase 5.5 stream-safety boundaries exist, but complete RelayREF and Output-side RelaySCN execution are not implemented,
- RelayLM does not deliver adapter transport or own frontend UI, ASR, TTS execution, audio generation, or avatar execution.

## Target architecture

The target managed request path adds broader compatibility-shape support, minimum active-transaction preservation, typed RelaySCN normalization/apply, and RelayLM-owned current-turn context reconstruction as the ordinary managed behavior.

The target realtime output path is:

```text
backend stream
  -> RelayCTX Stream Unpack
  -> safe output segmentation
  -> RelayREF
  -> Return-side RelayEMO hints
  -> Output-side RelaySCN
  -> approved visible segments
  -> external TTS / Avatar consumers
```

Current Phase 5.5 provides the bounded stream-safety and handoff-preparation subset of this path. Default-on complete output orchestration, adapter delivery, TTS/audio execution, and avatar control remain target behavior.

## Required migration

Required later work includes:

- broader instruction-bearing compatibility and active-transaction reconstruction,
- typed RelaySCN application from validated instruction interpretation,
- complete RelayREF and Output-side RelaySCN consumers,
- cancellation and partial-stream recovery beyond current fail-closed suppression,
- SOUL Lab Runtime adapter delivery and execution,
- external Open-LLM-VTuber end-to-end validation.

See [Open-LLM-VTuber Integration Design](open_llm_vtuber_integration.md), [Project Status](../PROJECT_STATUS.md), [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md), and [Pipeline Implementation Plan](pipeline_implementation_plan.md).
