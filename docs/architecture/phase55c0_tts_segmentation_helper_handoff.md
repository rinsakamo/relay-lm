---
relaylm_doc_type: implementation_handoff
relaylm_authority: bounded_slice_record
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - canonical architecture
  - future request-runtime SSE wiring
  - TTS execution
  - avatar adapter behavior
  - RelaySOUL persistence
---
# Phase 5.5-C0 TTS Segmentation Helper Handoff

## Summary

Phase 5.5-C0 adds a pure, helper-only TTS-safe segmentation foundation. It derives bounded character-range hints from already-safe visible output so a future downstream TTS adapter can split the same visible text without RelayLM executing TTS or owning audio/avatar control.

This slice is intentionally not wired into `/v1/chat/completions` streaming. It does not wrap `StreamingResponse`, inspect backend SSE bytes in runtime, or change Phase 5.5-B2 sequencing.

## Implemented files

```text
relaylm/relayctx_tts_segmentation.py
scripts/relaylm_relayctx_tts_segmentation_smoke.py
```

## Runtime-private helper

New helper:

```text
build_tts_safe_segmentation_hints(
    chunks,
    enabled,
    dry_run_only=True,
    max_segment_chars=120,
    min_segment_chars=8,
)
```

The helper accepts only already-safe visible string chunks. It returns `RelayCTXTTSHintResult` with optional `RelayCTXTTSHint` range hints.

Hints contain only character offsets, counts, boundary kind, flush recommendation, and reason IDs. They do not contain visible text, internal marker text, SSE payload bodies, TTS audio data, or avatar control data.

## Gate behavior

- `enabled=false`: no hints are emitted.
- `enabled=true` and `dry_run_only=true`: candidate hint count is computed, but no hints are emitted.
- `enabled=true` and `dry_run_only=false`: content-free character-range hints are emitted.
- non-string chunks fail closed and emit no hints.
- complete RelayCTX internal sentinels block hints.
- terminal partial RelayCTX sentinel prefixes block hints.

## Segmentation behavior

The helper emits boundaries for:

- Japanese and ASCII sentence punctuation,
- newline boundaries,
- bounded `max_segment_chars` fallback,
- final stream-end remainder.

The helper does not rewrite text. Downstream consumers must apply offsets against the original already-safe visible text if they need concrete segment strings.

## Diagnostics boundary

`build_relayctx_tts_segmentation_node_result(...)` emits node name:

```text
relayctx_tts_segmentation_hints
```

Diagnostics include only counts, gate booleans, status values, reason IDs, and safety flags. They omit hint arrays and all visible text.

## Smoke coverage

The smoke verifies:

- disabled gate emits no hints,
- dry-run plans hints without emission,
- enabled helper emits content-free offsets,
- Japanese punctuation and stream-end segmentation,
- length-limit fallback for punctuation-free text,
- internal sentinel blocking,
- terminal partial sentinel blocking,
- invalid chunk fail-closed behavior,
- node-result diagnostics omit raw visible/internal text.

Command:

```bash
python scripts/relaylm_relayctx_tts_segmentation_smoke.py
```

## Non-goals

This slice does not implement:

- request-runtime SSE interception,
- wrapping `StreamingResponse` output,
- Phase 5.5-B2 suppression runtime wiring,
- cancellation handling in runtime,
- backend stream failure recovery,
- TTS execution,
- avatar or Live2D control,
- MEM/SOUL/SLP persistence.

## Next slice

Recommended next product-critical runtime boundary remains:

```text
Phase 5.5-B2 request-runtime SSE suppression wiring
```

A later Phase 5.5-C runtime slice can consume safe visible output from B2 and pass these content-free range hints to a TTS adapter boundary.
