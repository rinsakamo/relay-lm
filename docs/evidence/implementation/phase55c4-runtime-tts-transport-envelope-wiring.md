---
relaylm_doc_type: evidence
relaylm_authority: historical_phase5_5_c4_runtime_tts_transport_envelope_wiring_implementation
relaylm_status: frozen
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_source_commit: 00c284b8729c048b89dbc19e9bbf23d427e218e8
relaylm_source_pr: 327
relaylm_recorded_on: 2026-06-21
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - canonical architecture
  - current runtime TTS handoff or transport-envelope behavior
  - current C0/C1/C3 node ordering or diagnostics schema
  - downstream adapter delivery
  - TTS execution
  - avatar adapter behavior
  - CTX/MEM/SOUL/SLP persistence
relaylm_related_authority:
  - ../../architecture/voice/streaming-and-tts.md
  - ../../contracts/runtime/tts-segmentation.md
  - ../../contracts/runtime/tts-transport.md
---
# Phase 5.5-C4 Runtime TTS Transport Envelope Wiring

> **Historical implementation evidence.** This frozen record describes the runtime-wiring C4 boundary merged in PR #327. Current Stream Unpack sequencing and runtime handoff/transport behavior are owned by the Phase 5.5 parent document, the current C2/C3 authorities, and implementation.

## Status

Phase 5.5-C4 wires the C3 TTS adapter transport envelope helper into the existing C2 stream-final runtime observer.

The runtime boundary remains intentionally narrow:

- it still runs only behind the existing default-off runtime TTS adapter handoff gate,
- it still observes only B2 apply-mode safe visible SSE output,
- it still passes backend SSE bytes through unchanged,
- it constructs C0 segmentation hints, C1 handoff plans, and C3 transport envelopes at stream finalization,
- it records only content-free node results,
- it does not deliver adapter transport,
- it does not execute TTS,
- it does not generate audio,
- it does not control Live2D/avatar adapters,
- it does not persist CTX/MEM/SOUL/SLP state.

## Implemented runtime boundary

Implemented files:

- `relaylm/relayctx_tts_adapter_handoff_runtime.py`
  - imports and invokes `build_tts_adapter_transport_envelope(...)`
  - records `relayctx_tts_adapter_transport` after C0 and C1 node results
  - preserves stream byte pass-through
- `scripts/relaylm_relayctx_tts_adapter_handoff_runtime_smoke.py`
  - updates stream-final node ordering to C0/C1/C3
  - verifies dry-run and ready transport-envelope diagnostics
  - verifies no delivery, TTS, audio, avatar, persistence, or external I/O
  - verifies stream-final trace output remains content-free
  - verifies invalid safe-output observation blocks both handoff and transport emission

## Runtime node ordering

When the existing runtime TTS handoff gate is enabled and B2 safe visible output is available, stream-final node results are recorded in this order:

```text
relayctx_tts_segmentation_hints
relayctx_tts_adapter_handoff
relayctx_tts_adapter_transport
```

If the runtime gate is disabled, or B2 safe visible output is unavailable, the wrapper remains byte-for-byte pass-through and records no C0/C1/C3 node results.

## Safety constraints

C4 does not add a new public request shape or new adapter I/O surface. It only constructs a runtime-private transport envelope and persists a content-free projection.

Persisted diagnostics must not include:

- raw visible text,
- raw SSE frames,
- backend payloads,
- internal RelayCTX marker literals,
- internal candidate bodies,
- raw C0 hint arrays,
- raw C1 handoff item arrays,
- raw C3 transport item arrays,
- adapter endpoint URLs,
- transport credentials,
- audio bytes,
- avatar commands.

The transport node result explicitly keeps:

```text
transport_delivery_requested = false
tts_execution_requested = false
audio_generation_requested = false
avatar_control_requested = false
persistence_allowed = false
external_io_performed = false
```

## Current non-goals

Phase 5.5-C4 still does not implement:

- downstream adapter delivery,
- transport endpoint configuration,
- TTS execution,
- audio generation,
- Live2D/avatar control,
- CTX/MEM/SOUL/SLP persistence,
- RelaySOUL apply/rollback/storage,
- response/control-envelope extraction,
- backend payload mutation,
- meaning-changing rewrite,
- non-stream Unpack behavior changes.

## Next slice

After C4, the remaining stream-adapter work is outside RelayLM core execution: define an external adapter bridge that can consume the runtime-private transport envelope without making RelayLM own TTS/audio/avatar execution.

Phase 6 asynchronous RelaySLP remains independently sequenced.
