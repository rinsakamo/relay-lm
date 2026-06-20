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

Phase 5.5 is the product-critical streaming boundary. Phase 5.5-A is complete as a pure direct-helper dry-run sentinel observer. Phase 5.5-B1 is complete as a direct-helper suppression gate. Phase 5.5-C0 is complete as a helper-only TTS segmentation foundation. Phase 5.5-C1 is complete as a helper-only TTS adapter handoff contract. Phase 5.5-B2 remains the next streaming runtime boundary.

This document tracks the bounded Stream Unpack implementation sequence.

## Purpose

Current streaming primarily preserves backend SSE forwarding. Non-stream RelayCTX Unpack already separates visible output from bounded internal candidates, but safe streaming requires additional chunk-level behavior.

Phase 5.5 exists to support:

- safe visible chunk forwarding,
- buffering across chunk boundaries for internal sentinels or envelopes,
- incomplete internal-candidate blocking,
- cancellation and partial-stream failure diagnostics,
- TTS-safe segmentation hints without owning TTS execution.

## Non-goals

Phase 5.5 does not:

- execute TTS,
- control Live2D or avatar adapters,
- persist MEM, SOUL, or SLP state,
- perform RelaySOUL apply, rollback, or storage writes,
- implement response/control-envelope extraction for client-instruction cache writing,
- rewrite visible response meaning,
- change backend model behavior,
- require RelaySOUL execution gates.

## Default posture

All apply-like behavior must remain gated.

```text
relayctx_stream_unpack_dry_run_enabled = false
relayctx_stream_unpack_dry_run_only = true
relayctx_stream_unpack_max_buffer_chars = 256
stream_tts_segmentation_hints_enabled = false  # target, not a current config field
```

Default behavior must preserve ordinary backend SSE forwarding.

Phase 5.5-A, B1, C0, and C1 currently provide direct-helper behavior only. They do not intercept request-runtime SSE.

When Stream Unpack is enabled for a future bounded runtime slice:

- visible chunks are preserved when safely recoverable,
- internal candidate markers are never exposed after detection,
- incomplete or malformed internal candidates are blocked,
- partial-stream failure records content-free diagnostics,
- no duplicate replay is allowed after a partial visible stream,
- TTS segmentation emits hints only; it does not call a TTS engine.

## Slice sequence

### Phase 5.5-A: stream sentinel buffer dry-run — complete

Implemented:

- `relaylm.relayctx_stream_unpack.observe_stream_sentinel_buffer(...)`,
- per-helper stream buffer state,
- bounded retained buffer window,
- detection of complete internal sentinels,
- detection of split internal sentinels across chunks,
- detection of terminal partial sentinel prefixes,
- content-free `RelayCTXStreamUnpackObservation`,
- content-free `relayctx_stream_unpack` PipelineNodeResult helper,
- default-off/dry-run-only config fields,
- direct smoke and dedicated CI workflow.

Not implemented in 5.5-A:

- runtime SSE interception,
- output suppression,
- visible chunk preservation after internal candidate detection,
- cancellation handling,
- duplicate replay prevention,
- TTS hints.

Exit criteria met:

- ordinary stream chunks are unchanged by helper design,
- internal marker split across chunks is detected in diagnostics,
- incomplete candidate at stream end is blocked as internal evidence,
- emitted diagnostics contain no raw streamed text.

See [Phase 5.5-A Stream Sentinel Buffer Dry-Run Handoff](phase55a_stream_sentinel_buffer_dry_run_handoff.md).

### Phase 5.5-B1: stream suppression gate helper — complete

Implemented:

- `relaylm.relayctx_stream_unpack.apply_stream_internal_suppression_gate(...)`,
- explicit `enabled` and `dry_run_only` gates,
- runtime-private `output_chunks`,
- content-free `RelayCTXStreamSuppressionResult`,
- content-free `relayctx_stream_suppression_gate` PipelineNodeResult helper,
- disabled-gate unchanged valid chunks,
- dry-run detection without output mutation,
- preservation of safe visible text before the first complete internal sentinel,
- suppression of complete and split internal sentinels when dry-run-only is disabled,
- terminal partial sentinel blocking,
- invalid non-string chunk fail-closed behavior,
- direct smoke coverage.

Not implemented in 5.5-B1:

- request-runtime SSE interception,
- wrapping `StreamingResponse` output,
- cancellation handling in runtime,
- backend stream failure recovery,
- duplicate replay prevention after runtime emission,
- TTS hints.

Exit criteria met:

- normal helper output remains unchanged when disabled or dry-run-only,
- visible text preceding a blocked internal candidate is preserved in helper apply mode,
- internal markers are not included in helper output after detection,
- diagnostics and node results contain no raw visible or internal stream text.

See [Phase 5.5-B1 Stream Suppression Gate Handoff](phase55b1_stream_suppression_gate_handoff.md).

### Phase 5.5-C0: TTS-safe segmentation helper — complete independently

Implemented:

- `relaylm.relayctx_tts_segmentation.build_tts_safe_segmentation_hints(...)`,
- content-free character-range `RelayCTXTTSHint` values,
- content-free `RelayCTXTTSHintResult` diagnostics,
- content-free `relayctx_tts_segmentation_hints` PipelineNodeResult helper,
- disabled-gate no-hint behavior,
- dry-run candidate hint counts without hint emission,
- Japanese/ASCII sentence punctuation boundaries,
- newline boundaries,
- bounded length-limit fallback,
- stream-end remainder boundary,
- complete and terminal-partial RelayCTX sentinel blocking,
- invalid non-string chunk fail-closed behavior,
- direct smoke coverage.

Not implemented in 5.5-C0:

- request-runtime SSE interception,
- wrapping `StreamingResponse` output,
- Phase 5.5-B2 suppression runtime wiring,
- runtime TTS adapter handoff,
- TTS execution,
- avatar control,
- cancellation handling or backend stream failure recovery.

Exit criteria met:

- hints are optional and default-off at helper level,
- dry-run computes only counts and emits no hints,
- enabled helper emits only content-free offsets and counts,
- hints are derived only from already-safe visible chunks,
- internal candidate material blocks hint emission,
- diagnostics and node results contain no raw visible or internal stream text.

See [Phase 5.5-C0 TTS Segmentation Helper Handoff](phase55c0_tts_segmentation_helper_handoff.md).

### Phase 5.5-C1: TTS adapter handoff contract — complete independently

Implemented:

- `relaylm.relayctx_tts_adapter_handoff.build_tts_adapter_handoff_plan(...)`,
- runtime-private `RelayCTXTTSAdapterHandoffPlan`,
- runtime-private content-free handoff items for future downstream adapter wiring,
- content-free `relayctx_tts_adapter_handoff` PipelineNodeResult helper,
- explicit `enabled` and `dry_run_only` gate,
- handoff candidate count and emitted handoff count separation,
- conservative propagation of C0 disabled, blocked, invalid, empty, dry-run, and ready states,
- diagnostics omitting visible text, hint arrays, and handoff item arrays,
- direct smoke coverage.

Not implemented in 5.5-C1:

- request-runtime SSE interception,
- wrapping `StreamingResponse` output,
- Phase 5.5-B2 suppression runtime wiring,
- actual downstream adapter transport,
- TTS execution,
- audio generation,
- avatar control,
- CTX/MEM/SOUL/SLP persistence.

Exit criteria met:

- C1 consumes C0 `RelayCTXTTSHintResult` values only,
- disabled and dry-run gates emit no handoff items,
- ready emits runtime-private content-free handoff items only when C0 is ready,
- C0 dry-run cannot become a C1 emitted handoff,
- blocked and invalid inputs fail closed,
- diagnostics and node results contain no raw visible text, raw hints, or handoff arrays,
- TTS/audio/avatar execution flags are always false.

See [Phase 5.5-C1 TTS Adapter Handoff Contract](phase55c1_tts_adapter_handoff_contract.md).

### Phase 5.5-B2: request-runtime SSE suppression wiring — planned next

Goal: safely wire the suppression helper into request-runtime streaming behind explicit gates while preserving default backend SSE forwarding.

Implemented behavior should include:

- route/config ownership for runtime Stream Unpack apply,
- unchanged ordinary SSE compatibility by default,
- runtime wrapping of backend bytes only when explicitly enabled,
- visible chunk preservation after safe emission,
- internal envelope suppression after detection,
- malformed candidate blocking,
- partial-stream failure summary,
- cancellation handling,
- duplicate replay prevention,
- content-free PipelineNodeResult projection.

Exit criteria:

- default streaming remains byte-for-byte backend forwarding,
- visible text preceding a blocked internal candidate remains preserved when safe,
- internal markers are not exposed after detection,
- malformed internal candidates do not trigger MEM/SOUL/SLP updates,
- cancellation produces a bounded content-free artifact,
- no duplicate replay occurs after visible chunks are emitted.

### Phase 5.5-C: TTS-safe segmentation and adapter handoff

Goal: emit bounded segmentation hints and runtime-private handoff plans for downstream TTS/adapters without owning audio generation.

Phase 5.5-C0 provides the pure segmentation helper foundation. Phase 5.5-C1 provides the pure adapter handoff contract helper. A later runtime slice must consume only safe visible output from the Phase 5.5-B runtime boundary and pass C0/C1 results across an adapter boundary without executing TTS.

Implemented behavior includes:

- punctuation and sentence-boundary hinting,
- conservative Japanese/Kana/CJK handling,
- bounded segment length hints,
- adapter handoff candidate/emitted count separation,
- runtime-private handoff plan shape,
- no TTS execution,
- no avatar control,
- no meaning-changing rewrite,
- no persistence side effect.

Exit criteria:

- TTS hints are optional and default-off,
- hints are derived from safe visible output only,
- hints contain no internal candidate text,
- adapter handoff logs omit raw hint arrays and handoff item arrays,
- fallback preserves raw visible text when segmentation is uncertain.

## Smoke matrix

Minimum smoke coverage should include:

| Case | Expected result |
|---|---|
| ordinary SSE chunks | unchanged forwarding in default mode |
| internal sentinel in one chunk | detected, content-free diagnostic emitted |
| internal sentinel split across chunks | detected by buffer state |
| terminal partial sentinel at stream end | blocked as internal evidence |
| visible text followed by internal candidate | safe visible text preserved, internal candidate blocked/suppressed |
| malformed internal candidate | candidate blocked, visible text preserved when safe |
| incomplete candidate at stream end | candidate blocked, no persistence update |
| cancellation after visible chunks | no duplicate replay, partial state recorded |
| backend stream failure before visible output | runtime failure recorded, no fabricated output |
| backend stream failure after visible output | emitted chunks preserved, recovery hint recorded |
| TTS hint disabled | no segmentation hint emitted |
| TTS hint enabled | hints derived only from safe visible text |
| TTS adapter handoff dry-run | candidates counted, emitted handoff count remains zero |
| TTS adapter handoff ready | runtime-private content-free handoff items emitted, logs omit arrays |

Phase 5.5-A covers the first four applicable dry-run/helper cases plus invalid chunk content-free failure. Phase 5.5-B1 covers direct-helper visible-prefix preservation, suppression, terminal partial blocking, invalid chunk fail-closed behavior, and content-free suppression node results. Phase 5.5-C0 covers helper-only TTS disabled, dry-run, enabled, length-fallback, internal-block, and content-free node-result cases. Phase 5.5-C1 covers helper-only adapter handoff disabled, dry-run, ready, blocked, invalid, empty, and content-free node-result cases. Runtime cases belong to Phase 5.5-B2.

## Safety invariants

Phase 5.5 must preserve these invariants:

- streaming compatibility by default,
- visible text is not rewritten for meaning,
- internal markers and candidate envelopes are not user-visible after detection,
- runtime-private content is not persisted in generic diagnostics,
- no MEM/SOUL/SLP mutation is triggered by malformed or incomplete candidates,
- no TTS or avatar execution is owned by RelayLM,
- RelayRUN handles runtime failures, cancellation, and checkpoint summaries,
- RelayCTX Unpack owns visible/internal separation; RelayREF and Output-side RelaySCN remain observation/policy consumers.

## RelaySOUL design freeze

Until Phase 5.5-B runtime wiring is complete, new RelaySOUL execution-gate design documents should not be added unless they directly unblock a current runtime safety issue.

Existing RelaySOUL gate documents remain valid historical/current governance references. The freeze is about avoiding additional design expansion while the streaming product-critical path still lacks request-runtime visible-chunk preservation and internal suppression.

## Next implementation handoff

The next implementation handoff should be:

```text
Phase 5.5-B2 request-runtime SSE suppression wiring
```

The handoff should include:

- runtime stream gate and config field ownership,
- unchanged ordinary SSE compatibility check,
- safe visible chunk preservation rules,
- internal marker/candidate suppression behavior,
- partial stream/cancellation behavior,
- no duplicate replay invariant,
- content-free diagnostic schema,
- explicit non-goals for TTS execution, RelaySOUL persistence, and response rewriting.
