---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase5_5_stream_unpack_bounded_slice_scope
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 5.5-C1 TTS adapter handoff helper changes
  - TTS adapter handoff diagnostics schema changes
  - C0 TTS segmentation hint result schema changes
relaylm_not_authoritative_for:
  - canonical pipeline responsibility order
  - request-runtime SSE wiring
  - TTS execution
  - Live2D or avatar adapter behavior
  - CTX/MEM/SOUL/SLP persistence
relaylm_related_authority:
  - phase5_5_stream_unpack_bounded_slice.md
  - phase55c0_tts_segmentation_helper_handoff.md
  - pipeline_implementation_plan.md
---
# Phase 5.5-C1 TTS Adapter Handoff Contract

## Status

Phase 5.5-C1 adds a pure helper that converts Phase 5.5-C0 `RelayCTXTTSHintResult` values into a runtime-private downstream adapter handoff plan.

This phase does not wire the plan into request-runtime SSE, execute TTS, generate audio, control avatars, mutate visible output, or persist CTX/MEM/SOUL/SLP state.

## Implemented boundary

Implemented files:

```text
relaylm/relayctx_tts_adapter_handoff.py
scripts/relaylm_relayctx_tts_adapter_handoff_smoke.py
.github/workflows/relayctx-tts-adapter-handoff-smoke.yml
```

The helper accepts:

```text
RelayCTXTTSHintResult
```

and returns:

```text
RelayCTXTTSAdapterHandoffPlan
```

The plan may contain runtime-private handoff items when both the C0 hint result and the C1 gate are ready. The node-result/log projection omits the item array.

## Gate behavior

C1 owns its own explicit gate:

- `enabled=false`: `disabled`, no handoff candidates or emitted items,
- `enabled=true` and `dry_run_only=true`: candidate count can be planned, emitted count remains zero,
- `enabled=true` and `dry_run_only=false`: runtime-private handoff items can be emitted only when the source C0 result is `ready`.

Upstream C0 status is preserved conservatively:

- C0 `dry_run_ready` keeps C1 in `dry_run_ready` because C0 emitted no runtime-private hint items,
- C0 `blocked` maps to C1 `blocked`,
- C0 `invalid_input` maps to C1 `invalid_input`,
- C0 `empty_input` maps to C1 `empty_input`,
- C0 `disabled` maps to C1 `blocked` with `source_hints_disabled` when C1 is enabled.

## Diagnostics boundary

Diagnostics include only:

- status values,
- gate booleans,
- source hint counts,
- handoff candidate/emitted counts,
- execution-request booleans,
- reason IDs,
- content-free flags.

Diagnostics do not include:

- visible text,
- raw hint arrays,
- handoff item arrays,
- internal marker literals,
- internal candidate bodies,
- SSE frames,
- audio bytes,
- avatar control payloads.

## Non-execution guarantees

The plan and node result always keep:

```text
tts_execution_requested = false
audio_generation_requested = false
avatar_control_requested = false
persistence_allowed = false
```

No C1 helper path calls a TTS engine, creates audio, controls Live2D/avatar adapters, stores visible text, or writes MEM/SOUL/SLP state.

## Smoke coverage

The smoke verifies:

- disabled gate emits no handoff,
- dry-run plans candidates without emission,
- ready emits runtime-private content-free handoff items,
- upstream C0 dry-run cannot emit handoff items,
- upstream blocked result blocks handoff,
- upstream invalid result fails closed,
- empty source emits no handoff,
- non-result input fails closed,
- node result/log projection omits visible text, raw hints, and handoff arrays,
- TTS/audio/avatar execution flags are always false,
- persistence is never allowed.

## Next slice

A later runtime slice can connect safe visible stream output as:

```text
safe visible output -> C0 segmentation hints -> C1 adapter handoff plan
```

That later slice must still keep actual TTS execution and avatar control outside RelayLM, likely in SOUL Lab runtime adapter work.
