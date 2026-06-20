---
relaylm_doc_type: implementation_plan
relaylm_authority: phase5_5_stream_unpack_bounded_slice_scope
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Stream Unpack slice status changes
  - streaming response boundary changes
  - TTS-safe segmentation contract changes
  - output-side internal candidate handling changes
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact final stream transport schema
  - TTS engine execution
  - Live2D or avatar adapter behavior
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_responsibility_design.md
  - pipeline_implementation_plan.md
  - current_target_migration_guide.md
---
# Phase 5.5 Stream Unpack Bounded Slice

## Status

Phase 5.5 is the product-critical streaming boundary. Phase 5.5-A, B1, B2, C0, C1, and C2 are complete as bounded, default-off slices.

Implemented through this document:

- Phase 5.5-A: pure direct-helper stream sentinel dry-run observation,
- Phase 5.5-B1: direct-helper stream suppression gate,
- Phase 5.5-B2: gated request-runtime SSE suppression wiring,
- Phase 5.5-C0: helper-only TTS-safe segmentation hints,
- Phase 5.5-C1: helper-only TTS adapter handoff contract,
- Phase 5.5-C2: default-off runtime wiring from B2 safe visible output into C0/C1 content-free node results.

RelayLM still does not execute TTS, generate audio, control avatars, or persist CTX/MEM/SOUL/SLP state from the stream path.

## Purpose

Current streaming preserves backend SSE forwarding by default. Non-stream RelayCTX Unpack already separates visible output from bounded internal candidates, but safe streaming requires additional chunk-level behavior.

Phase 5.5 exists to support:

- safe visible chunk forwarding,
- buffering across chunk boundaries for internal sentinels or envelopes,
- incomplete internal-candidate blocking,
- cancellation and partial-stream failure diagnostics,
- TTS-safe segmentation hints and adapter handoff metadata without owning TTS execution.

## Non-goals

Phase 5.5 does not:

- execute TTS,
- generate audio,
- control Live2D or avatar adapters,
- persist MEM, SOUL, CTX, or SLP state,
- perform RelaySOUL apply, rollback, or storage writes,
- implement response/control-envelope extraction for client-instruction cache writing,
- rewrite visible response meaning,
- change backend model behavior,
- require RelaySOUL execution gates.

## Default posture

All apply-like behavior remains explicitly gated.

```text
relayctx_stream_unpack_dry_run_enabled = false
relayctx_stream_unpack_dry_run_only = true
relayctx_stream_unpack_max_buffer_chars = 256
relayctx_tts_adapter_handoff_runtime_enabled = false
relayctx_tts_adapter_handoff_runtime_dry_run_only = true
relayctx_tts_adapter_handoff_max_segment_chars = 120
relayctx_tts_adapter_handoff_min_segment_chars = 8
```

Default behavior preserves ordinary backend SSE forwarding. B2 can wrap request-runtime streaming only when the stream gate is explicitly enabled. C2 can observe runtime bytes only after B2 apply mode has produced safe visible output.

## Slice sequence

### Phase 5.5-A: stream sentinel buffer dry-run — complete

Implemented:

- `relaylm.relayctx_stream_unpack.observe_stream_sentinel_buffer(...)`,
- per-helper stream buffer state,
- bounded retained buffer window,
- complete/split/terminal-partial internal sentinel detection,
- content-free observation and PipelineNodeResult projection,
- default-off/dry-run-only config fields,
- direct smoke and dedicated CI workflow.

See [Phase 5.5-A Stream Sentinel Buffer Dry-Run Handoff](phase55a_stream_sentinel_buffer_dry_run_handoff.md).

### Phase 5.5-B1: stream suppression gate helper — complete

Implemented:

- `relaylm.relayctx_stream_unpack.apply_stream_internal_suppression_gate(...)`,
- explicit enabled/dry-run gate,
- runtime-private `output_chunks`,
- visible-prefix preservation,
- complete/split internal sentinel suppression,
- terminal partial sentinel blocking,
- invalid chunk fail-closed behavior,
- content-free node result and direct smoke coverage.

See [Phase 5.5-B1 Stream Suppression Gate Handoff](phase55b1_stream_suppression_gate_handoff.md).

### Phase 5.5-B2: request-runtime SSE suppression wiring — complete

Implemented:

- `relaylm.relayctx_stream_suppression_runtime.wrap_stream_with_relayctx_suppression(...)`,
- request-runtime wrapping of backend SSE bytes behind `relayctx_stream_unpack_dry_run_enabled`,
- byte-for-byte pass-through when disabled or dry-run-only,
- OpenAI-compatible SSE `data:` frame handling for streamed content fields,
- visible-prefix preservation in apply mode,
- complete and split internal sentinel suppression in apply mode,
- terminal partial sentinel blocking,
- invalid UTF-8, invalid SSE JSON, ambiguous content fields, and backend iterator errors fail-closed,
- no duplicate replay after visible chunks are emitted,
- content-free `relayctx_stream_suppression_gate` node result,
- runtime smoke coverage.

See [Phase 5.5-B2 Stream Suppression Runtime Wiring Handoff](phase55b2_stream_suppression_runtime_handoff.md).

### Phase 5.5-C0: TTS-safe segmentation helper — complete

Implemented:

- `relaylm.relayctx_tts_segmentation.build_tts_safe_segmentation_hints(...)`,
- content-free character-range `RelayCTXTTSHint` values,
- content-free `RelayCTXTTSHintResult` diagnostics,
- content-free `relayctx_tts_segmentation_hints` node result,
- disabled/dry-run/ready/empty/blocked/invalid status behavior,
- Japanese/ASCII sentence punctuation, newline, length-limit, and stream-end boundaries,
- internal sentinel blocking,
- direct smoke coverage.

See [Phase 5.5-C0 TTS Segmentation Helper Handoff](phase55c0_tts_segmentation_helper_handoff.md).

### Phase 5.5-C1: TTS adapter handoff contract — complete

Implemented:

- `relaylm.relayctx_tts_adapter_handoff.build_tts_adapter_handoff_plan(...)`,
- runtime-private `RelayCTXTTSAdapterHandoffPlan`,
- runtime-private content-free handoff items for future downstream adapter wiring,
- content-free `relayctx_tts_adapter_handoff` node result,
- explicit enabled/dry-run gate,
- candidate/emitted count separation,
- conservative C0 status propagation,
- diagnostics omitting visible text, hint arrays, and handoff item arrays,
- direct smoke coverage.

See [Phase 5.5-C1 TTS Adapter Handoff Contract](phase55c1_tts_adapter_handoff_contract.md).

### Phase 5.5-C2: runtime TTS adapter handoff wiring — complete

Implemented:

- `relaylm.relayctx_tts_adapter_handoff_runtime.wrap_stream_with_tts_adapter_handoff(...)`,
- pass-through observation of B2 apply-mode safe visible SSE output,
- explicit `relayctx_tts_adapter_handoff_runtime_enabled` and dry-run-only gates,
- C0 segmentation invocation from runtime-private safe visible chunks,
- C1 adapter handoff planning from C0 results,
- C0/C1 node result recording at stream end,
- no stream-byte mutation,
- no C0/C1 invocation when B2 safe output is unavailable,
- invalid observation blocking handoff emission,
- direct runtime smoke and dedicated CI workflow.

See [Phase 5.5-C2 Runtime TTS Adapter Handoff Wiring](phase55c2_runtime_tts_adapter_handoff_wiring.md).

## Smoke matrix

Minimum smoke coverage includes:

| Case | Expected result |
|---|---|
| ordinary SSE chunks | unchanged forwarding in default mode |
| internal sentinel in one chunk | detected, content-free diagnostic emitted |
| internal sentinel split across chunks | detected by buffer state |
| terminal partial sentinel at stream end | blocked as internal evidence |
| visible text followed by internal candidate | safe visible text preserved, internal candidate blocked/suppressed |
| malformed internal candidate | candidate blocked, visible text preserved when safe |
| incomplete candidate at stream end | candidate blocked, no persistence update |
| backend stream failure before/after visible output | fail-closed diagnostics, no duplicate replay |
| TTS hint disabled/dry-run/ready | content-free C0 projection only |
| TTS adapter handoff dry-run/ready | content-free C1 projection only, no execution |
| C2 with B2 safe output | C0/C1 runtime node results recorded |
| C2 without B2 safe output | C0/C1 are not invoked |
| C2 invalid observation | handoff is blocked content-free |

## Safety invariants

Phase 5.5 preserves these invariants:

- streaming compatibility by default,
- visible text is not rewritten for meaning,
- internal markers and candidate envelopes are not user-visible after detection,
- runtime-private content is not persisted in generic diagnostics,
- no MEM/SOUL/SLP mutation is triggered by malformed or incomplete candidates,
- no TTS/audio/avatar execution is owned by RelayLM,
- RelayRUN handles runtime failures, cancellation, and checkpoint summaries,
- RelayCTX Unpack owns visible/internal separation; RelayREF and output-side RelaySCN remain observation/policy consumers.

## RelaySOUL design freeze

The Phase 5.5-B runtime wiring boundary is closed for bounded SSE suppression, and C2 closes runtime C0/C1 handoff planning. New RelaySOUL execution-gate design documents should still be avoided unless they directly unblock a current runtime safety issue or are part of the later SOUL Lab runtime adapter boundary.

## Next implementation handoff

The next implementation handoff should not move TTS execution into RelayLM core. A future adapter-facing slice may define a default-off downstream transport contract for handing runtime-private C1 metadata to an external TTS/avatar adapter layer.
