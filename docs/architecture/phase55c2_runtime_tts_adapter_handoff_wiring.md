---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase5_5_stream_unpack_bounded_slice_scope
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 5.5-C2 runtime TTS handoff wiring changes
  - runtime stream handoff diagnostics schema changes
  - C0/C1 runtime invocation rules change
relaylm_not_authoritative_for:
  - canonical pipeline responsibility order
  - TTS engine execution
  - Live2D/avatar adapter behavior
  - CTX/MEM/SOUL/SLP persistence
relaylm_related_authority:
  - phase5_5_stream_unpack_bounded_slice.md
  - pipeline_implementation_plan.md
  - pipeline_responsibility_design.md
---
# Phase 5.5-C2 Runtime TTS Adapter Handoff Wiring

## Status

Phase 5.5-C2 wires the C0 TTS segmentation helper and C1 adapter handoff contract into request-runtime streaming after the Phase 5.5-B2 suppression wrapper.

The C2 wiring is intentionally narrow:

- it observes only bytes emitted after B2 suppression apply mode,
- it passes stream bytes through unchanged,
- it records C0 and C1 content-free node results,
- it does not execute TTS,
- it does not generate audio,
- it does not control Live2D/avatar adapters,
- it does not persist CTX/MEM/SOUL/SLP state.

## Implemented runtime boundary

Implemented files:

- `relaylm/relayctx_tts_adapter_handoff_runtime.py`
  - `wrap_stream_with_tts_adapter_handoff(...)`
  - pass-through observer for already-safe visible SSE output
  - C0 segmentation invocation from runtime-private safe visible chunks
  - C1 adapter handoff plan invocation from C0 result
- `relaylm/adapter.py`
  - applies C2 only when its explicit route gate is enabled
  - supplies the B2-safe-output precondition to the runtime observer
- `relaylm/config.py` and `relaylm/routing.py`
  - default-off C2 route/config gates
- `scripts/relaylm_relayctx_tts_adapter_handoff_runtime_smoke.py`
  - direct runtime wrapper smoke coverage
- `.github/workflows/relayctx-tts-adapter-handoff-runtime-smoke.yml`
  - compile and direct runtime smoke workflow

## Gate behavior

C2 config fields are default-off:

```text
relayctx_tts_adapter_handoff_runtime_enabled = false
relayctx_tts_adapter_handoff_runtime_dry_run_only = true
relayctx_tts_adapter_handoff_max_segment_chars = 120
relayctx_tts_adapter_handoff_min_segment_chars = 8
```

C2 can observe runtime bytes only when both are true:

```text
relayctx_tts_adapter_handoff_runtime_enabled = true
relayctx_stream_unpack_dry_run_enabled = true
relayctx_stream_unpack_dry_run_only = false
```

If the B2 safe-output precondition is not met, C2 passes bytes through and does not invoke C0 or C1. This prevents raw backend stream bytes or B2 dry-run observations from becoming TTS hint sources.

## Diagnostics constraints

C2 records only existing content-free C0/C1 node projections:

- `relayctx_tts_segmentation_hints`,
- `relayctx_tts_adapter_handoff`.

Diagnostics must not include:

- raw visible text,
- raw SSE frames,
- backend payloads,
- internal RelayCTX marker literals,
- internal candidate bodies,
- raw hint arrays,
- raw handoff item arrays,
- audio bytes,
- avatar commands.

Allowed diagnostics are limited to:

- status / decision,
- counts,
- booleans,
- configured segment limits,
- reason IDs,
- content-free artifact metadata.

## Current non-goals

Phase 5.5-C2 still does not implement:

- TTS execution,
- audio generation,
- Live2D/avatar control,
- downstream adapter transport,
- CTX/MEM/SOUL/SLP persistence,
- RelaySOUL apply/rollback/storage,
- response/control-envelope extraction,
- backend payload mutation,
- meaning-changing rewrite,
- non-stream Unpack behavior changes.

## Smoke coverage

Runtime smoke covers:

- dry-run C2 consuming B2 safe visible output and emitting candidate counts only,
- ready C2 emitting runtime-private C1 handoff items without TTS/audio/avatar execution,
- no C0/C1 invocation when the B2 safe-output precondition is absent,
- invalid safe-output observation blocking C0/C1 handoff,
- content-free diagnostics for C0 and C1 runtime node results.

## Next slice

The next bounded slice should not execute TTS directly inside RelayLM. A later adapter-facing slice may define an in-process adapter transport contract, still default-off and still preserving RelayLM's ownership boundary: RelayLM may produce runtime-private handoff metadata, while TTS/audio/avatar execution remains outside RelayLM core.
