---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase5_5_stream_unpack_bounded_slice_scope
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 5.5-C3 adapter-facing TTS transport contract changes
  - adapter transport envelope diagnostics schema changes
  - C1 transport consumer rules change
relaylm_not_authoritative_for:
  - canonical pipeline responsibility order
  - request-runtime stream wiring
  - TTS engine execution
  - Live2D/avatar adapter behavior
  - CTX/MEM/SOUL/SLP persistence
relaylm_related_authority:
  - phase5_5_stream_unpack_bounded_slice.md
  - pipeline_implementation_plan.md
  - pipeline_responsibility_design.md
---
# Phase 5.5-C3 TTS Adapter Transport Contract

## Status

Phase 5.5-C3 defines a helper-only adapter-facing transport contract from the Phase 5.5-C1 runtime-private handoff plan.

The C3 boundary is intentionally narrow:

- it consumes only a `RelayCTXTTSAdapterHandoffPlan`,
- it produces a runtime-private `RelayCTXTTSAdapterTransportEnvelope`,
- it preserves content-free persisted diagnostics,
- it does not wire into request-runtime streaming,
- it does not send transport I/O,
- it does not execute TTS,
- it does not generate audio,
- it does not control Live2D/avatar adapters,
- it does not persist CTX/MEM/SOUL/SLP state.

## Implemented helper boundary

Implemented files:

- `relaylm/relayctx_tts_adapter_transport.py`
  - `build_tts_adapter_transport_envelope(...)`
  - runtime-private content-free `RelayCTXTTSAdapterTransportItem`
  - runtime-private content-free `RelayCTXTTSAdapterTransportEnvelope`
  - `build_relayctx_tts_adapter_transport_node_result(...)`
- `scripts/relaylm_relayctx_tts_adapter_transport_smoke.py`
  - direct helper smoke coverage
- `.github/workflows/relayctx-tts-adapter-transport-smoke.yml`
  - compile and direct helper smoke workflow

## Contract behavior

C3 accepts only a C1 `RelayCTXTTSAdapterHandoffPlan` as source input.

Status propagation is conservative:

| C1 handoff status | C3 transport status |
|---|---|
| `ready` + C3 dry-run-only | `dry_run_ready` |
| `ready` + C3 apply gate | `ready` |
| `dry_run_ready` | `dry_run_ready` |
| `empty_input` | `empty_input` |
| `blocked` | `blocked` |
| `invalid_input` | `invalid_input` |
| `disabled` while C3 enabled | `blocked` |
| non-C1 object | `invalid_input` |

Even when C3 status is `ready`, the helper only emits runtime-private transport envelope items. It does not deliver those items to any adapter, endpoint, process, TTS engine, audio generator, avatar controller, or persistent store.

## Diagnostics constraints

C3 records only content-free node projections:

- `relayctx_tts_adapter_transport`.

Diagnostics must not include:

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

Allowed diagnostics are limited to:

- status / decision,
- source C1 status,
- counts,
- booleans,
- reason IDs,
- content-free artifact metadata.

## Current non-goals

Phase 5.5-C3 still does not implement:

- request-runtime C3 invocation,
- downstream adapter delivery,
- TTS execution,
- audio generation,
- Live2D/avatar control,
- CTX/MEM/SOUL/SLP persistence,
- RelaySOUL apply/rollback/storage,
- response/control-envelope extraction,
- backend payload mutation,
- meaning-changing rewrite,
- non-stream Unpack behavior changes.

## Smoke coverage

Direct smoke covers:

- disabled gate emits no transport items,
- dry-run C3 plans candidates without emission,
- ready C3 emits runtime-private content-free transport items,
- source dry-run C1 handoff cannot emit C3 transport items,
- blocked C1 handoff blocks C3 transport,
- invalid C1 handoff fails closed,
- empty source emits no transport items,
- non-C1 input fails closed,
- diagnostics omit visible text, internal markers, handoff items, transport items, audio, avatar commands, and transport I/O.

## Next slice

The next bounded slice should still avoid TTS execution inside RelayLM core. A later runtime-facing slice may optionally wire C3 envelope construction after C2 stream-final handoff planning, while preserving default-off behavior and leaving delivery/execution to an external adapter layer.
