---
relaylm_doc_type: evidence
relaylm_authority: historical_phase5_5_b1_stream_suppression_gate_implementation
relaylm_status: frozen
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_source_commit: 062d597fbff32a9d3a68bc3d1f10ff6850113451
relaylm_source_pr: 312
relaylm_recorded_on: 2026-06-20
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - canonical architecture
  - current request-runtime SSE wiring
  - current diagnostics or configuration schema
  - TTS execution
  - RelaySOUL persistence
relaylm_related_authority:
  - ../../architecture/phase5_5_stream_unpack_bounded_slice.md
  - ../../architecture/phase55b2_stream_suppression_runtime_handoff.md
---
# Phase 5.5-B1 Stream Suppression Gate Handoff

> **Historical implementation evidence.** This frozen record describes the helper-only B1 boundary merged in PR #312. Current Stream Unpack sequencing is owned by the Phase 5.5 parent document, and current request-runtime suppression behavior is owned by the B2 handoff and implementation.

## Summary

Phase 5.5-B1 adds the first visible/internal stream separation gate as a pure helper. It preserves already-safe visible text before a RelayCTX internal sentinel and suppresses or blocks internal candidate material when the explicit gate is enabled and dry-run-only is disabled.

This slice is intentionally not wired into `/v1/chat/completions` streaming yet. Ordinary runtime SSE forwarding remains unchanged.

## Implemented files

```text
relaylm/relayctx_stream_unpack.py
scripts/relaylm_relayctx_stream_unpack_sentinel_smoke.py
```

The existing `RelayCTX stream unpack sentinel smoke` workflow covers the new helper through the existing stream-unpack path filters.

## Runtime-private helper

New helper:

```text
apply_stream_internal_suppression_gate(
    chunks,
    enabled,
    dry_run_only=True,
    max_buffer_chars=256,
)
```

The helper returns `RelayCTXStreamSuppressionResult` with runtime-private `output_chunks` plus content-free diagnostics. `output_chunks` must not be persisted through generic diagnostics.

## Gate behavior

- `enabled=false`: valid string chunks are returned unchanged.
- `enabled=true` and `dry_run_only=true`: internal sentinel candidates are detected, but output chunks remain unchanged.
- `enabled=true` and `dry_run_only=false`: visible text before the first complete internal sentinel is preserved, while the sentinel and following candidate material are suppressed.
- terminal partial sentinel prefixes are blocked by preserving only the safe visible prefix before the partial marker.
- invalid non-string chunks fail closed and emit no output chunks.

## Diagnostics boundary

`build_relayctx_stream_suppression_node_result(...)` emits node name:

```text
relayctx_stream_suppression_gate
```

Diagnostics include only counts, status, gate booleans, and reason IDs. They do not expose visible text, internal marker text, candidate bodies, SSE payload bodies, TTS segments, or persistence content.

## Smoke coverage

The smoke verifies:

- disabled gate preserves chunks,
- dry-run detects suppression candidates without mutation,
- enabled apply preserves safe visible prefix and suppresses internal material,
- split internal markers are detected and suppressed,
- terminal partial markers are blocked,
- invalid chunks fail closed,
- node-result diagnostics remain content-free.

Command:

```bash
python scripts/relaylm_relayctx_stream_unpack_sentinel_smoke.py
```

## Non-goals

This slice does not implement:

- request-runtime SSE interception,
- wrapping `StreamingResponse` output,
- cancellation handling in runtime,
- backend stream failure recovery,
- TTS-safe segmentation hints,
- TTS or avatar execution,
- MEM/SOUL/SLP persistence.

## Next slice

Recommended next implementation boundary:

```text
Phase 5.5-B2 request-runtime SSE suppression wiring
```

That slice should wrap streaming bytes only behind explicit runtime gates, preserve ordinary SSE compatibility by default, record partial stream/cancellation diagnostics, and avoid duplicate replay after any visible chunk has been emitted.
