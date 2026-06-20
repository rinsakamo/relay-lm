---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase5_5_stream_unpack_bounded_slice_scope
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 5.5-B2 runtime wiring changes
  - streaming response wrapper behavior changes
  - RelayCTX stream suppression diagnostics schema changes
relaylm_not_authoritative_for:
  - canonical pipeline responsibility order
  - TTS execution or Live2D/avatar control
  - RelaySOUL apply/rollback/storage
  - CTX/MEM/SOUL/SLP persistence
relaylm_related_authority:
  - phase5_5_stream_unpack_bounded_slice.md
  - pipeline_implementation_plan.md
  - pipeline_responsibility_design.md
---
# Phase 5.5-B2 Stream Suppression Runtime Wiring Handoff

## Status

Phase 5.5-B2 wires the Phase 5.5-B1 stream suppression gate into request-runtime streaming behind explicit config gates.

The runtime wiring is intentionally narrow:

- `open_chat_completion_stream(...)` still owns backend connection setup and returns `AsyncIterator[bytes]`.
- The stream wrapper is applied only when `relayctx_stream_unpack_dry_run_enabled=true` is present on the resolved route.
- `relayctx_stream_unpack_dry_run_only=true` remains byte-for-byte pass-through while recording content-free detection diagnostics.
- Suppression apply can occur only when `relayctx_stream_unpack_dry_run_enabled=true` and `relayctx_stream_unpack_dry_run_only=false`.

## Implemented runtime boundary

Implemented files:

- `relaylm/relayctx_stream_suppression_runtime.py`
  - `wrap_stream_with_relayctx_suppression(...)`
  - byte/SSE wrapper for backend `AsyncIterator[bytes]`
  - bounded pending visible buffer for split-sentinel detection
  - content-free `relayctx_stream_suppression_gate` PipelineNodeResult recording
- `relaylm/adapter.py`
  - wraps the backend stream iterator only when the route has stream unpack dry-run enabled
- `relaylm/routing.py`
  - propagates stream unpack config fields to `ResolvedRoute`
- `scripts/relaylm_relayctx_stream_suppression_runtime_smoke.py`
  - runtime wrapper smoke coverage
- `.github/workflows/relayctx-stream-unpack-sentinel-smoke.yml`
  - runs both direct-helper and runtime-wrapper smoke scripts

## Safety behavior

Default-off behavior:

- If `relayctx_stream_unpack_dry_run_enabled=false`, adapter streaming is not wrapped.
- Backend SSE bytes remain the existing pass-through path.

Dry-run-only behavior:

- If `relayctx_stream_unpack_dry_run_enabled=true` and `relayctx_stream_unpack_dry_run_only=true`, the wrapper yields the original bytes unchanged.
- It observes OpenAI-compatible SSE `data:` frames for streamed `choices[*].delta.content` / `choices[*].text` fragments.
- Diagnostics remain content-free: counts, booleans, statuses, and reason IDs only.

Apply behavior:

- If `relayctx_stream_unpack_dry_run_enabled=true` and `relayctx_stream_unpack_dry_run_only=false`, the wrapper suppresses RelayCTX internal marker/candidate material from user-visible SSE output.
- Safe visible text before the first complete or terminal-partial internal marker is preserved when recoverable.
- `[DONE]` is preserved to keep OpenAI-compatible stream termination behavior.
- Invalid bytes, invalid SSE JSON, non-byte stream chunks, and backend iterator failures are recorded as fail-closed `invalid_input` diagnostics.
- Already emitted visible chunks are not replayed.

## Diagnostics constraints

The runtime node result uses the existing `relayctx_stream_suppression_gate` node name and `relayctx_stream_suppression.v0` schema.

Diagnostics must not include:

- raw SSE frames,
- user-visible text,
- internal marker literals,
- internal candidate bodies,
- backend payloads,
- response text.

Allowed diagnostics are limited to:

- status / decision,
- counts,
- booleans,
- buffer limit,
- reason IDs,
- content-free artifact metadata.

## Current non-goals

Phase 5.5-B2 still does not implement:

- TTS-safe segmentation hints,
- TTS execution,
- Live2D/avatar control,
- CTX/MEM/SOUL/SLP persistence,
- RelaySOUL apply/rollback/storage,
- response/control-envelope extraction,
- backend payload mutation,
- meaning-changing rewrite,
- non-stream Unpack behavior changes.

## Smoke coverage

Runtime smoke covers:

- default-off wrapper pass-through,
- dry-run-only pass-through with detection,
- apply-mode visible-prefix preservation,
- marker detection across SSE frames,
- marker detection across byte chunks,
- terminal partial marker blocking,
- invalid UTF-8 fail-closed behavior,
- backend iterator error without duplicate replay,
- content-free diagnostics and node result projection.

## Next slice

The next bounded slice should be Phase 5.5-C: TTS-safe segmentation hints.

Phase 5.5-C should derive hints only from safe visible output and should remain default-off. It must not execute TTS, call avatar adapters, persist state, or expose internal RelayCTX candidates.
