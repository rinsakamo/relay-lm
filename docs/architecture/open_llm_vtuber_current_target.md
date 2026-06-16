# Open-LLM-VTuber Current / Target Boundary

## Current implemented

Open-LLM-VTuber is an optional OpenAI-compatible frontend path:

```text
Open-LLM-VTuber -> RelayLM -> OpenAI-compatible backend
```

Current behavior:

- streaming is primarily backend SSE forwarding,
- default-off `client_history_exclusion_apply.v0` supports only managed requests with no client system/developer messages,
- actual apply retains one RelayLM-owned compiled prefix and the validated current user message,
- explicit actual apply blocks forwarding when no exact applied result exists,
- Stream Unpack, safe segmentation, RelayREF, and complete Output-side RelaySCN are not implemented,
- RelayLM does not own frontend UI, ASR, TTS execution, or avatar execution.

## Target architecture

The target managed request path adds bounded low-trust current-instruction evidence, active transaction preservation, prior-history exclusion, RelaySCN normalization, and RelayLM-owned context reconstruction.

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

These target stages are not current runtime behavior.

## Required migration

Update instruction-bearing managed apply, active-transaction preservation, Stream Unpack, segmentation, RelayREF, Output-side RelaySCN, cancellation/duplicate handling, and external end-to-end smoke coverage together.

See [Open-LLM-VTuber Integration Design](open_llm_vtuber_integration.md), [Project Status](../PROJECT_STATUS.md), and [Pipeline Implementation Plan](pipeline_implementation_plan.md).
