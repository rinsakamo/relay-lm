---
relaylm_doc_type: implementation_handoff
relaylm_authority: bounded_slice_record
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - canonical architecture
  - future Stream Unpack apply behavior
  - TTS execution
  - RelaySOUL persistence
---
# Phase 5.5-A Stream Sentinel Buffer Dry-Run Handoff

## Summary

Phase 5.5-A adds the first Stream Unpack implementation slice: a pure, content-free sentinel observer for streamed text fragments.

The slice is intentionally diagnostics-only. It observes chunks for RelayCTX internal sentinels across chunk boundaries, but it does not mutate outgoing SSE events, suppress output, emit TTS hints, or persist CTX/MEM/SOUL/SLP state.

## Implemented files

```text
relaylm/relayctx_stream_unpack.py
scripts/relaylm_relayctx_stream_unpack_sentinel_smoke.py
.github/workflows/relayctx-stream-unpack-sentinel-smoke.yml
```

Related config/docs updates:

```text
relaylm/config.py
config.example.yaml
docs/PROJECT_STATUS.md
docs/architecture/pipeline_implementation_plan.md
docs/architecture/phase5_5_stream_unpack_bounded_slice.md
```

## Runtime boundary

Implemented helper:

```text
observe_stream_sentinel_buffer(chunks, max_buffer_chars=256)
```

The helper returns a content-free `RelayCTXStreamUnpackObservation` with:

- chunk counts,
- observed character counts,
- retained buffer length,
- complete sentinel detection,
- split sentinel detection,
- terminal partial sentinel detection,
- blocked reason IDs,
- invariant booleans showing output mutation and persistence are not allowed.

It does not expose raw chunk text, internal marker text, backend payloads, response bodies, or TTS segments.

## Config boundary

New config fields are default-off / dry-run-only:

```yaml
relayctx_stream_unpack_dry_run_enabled: false
relayctx_stream_unpack_dry_run_only: true
relayctx_stream_unpack_max_buffer_chars: 256
```

This slice does not wire the helper into `/v1/chat/completions`. The fields define the future runtime gate and keep copy-ready config exhaustive.

## Node result boundary

`build_relayctx_stream_unpack_node_result(...)` emits a content-free `PipelineNodeResult` with node name:

```text
relayctx_stream_unpack
```

Status mapping:

```text
clean -> diagnostic_only
sentinel_detected -> blocked
partial_sentinel -> blocked
invalid_input -> failed
```

The node result is direct-helper only in this slice; request-runtime wiring is later work.

## Smoke coverage

The direct smoke verifies:

- ordinary streamed text remains dry-run/unchanged,
- complete internal sentinel in one chunk is detected,
- split internal sentinel across chunks is detected,
- terminal partial sentinel prefix is blocked as internal evidence,
- invalid non-string chunks fail closed,
- diagnostics and node-result logs remain content-free.

Command:

```bash
python scripts/relaylm_relayctx_stream_unpack_sentinel_smoke.py
```

CI workflow:

```text
RelayCTX stream unpack sentinel smoke
```

## Non-goals

This slice does not implement:

- runtime SSE interception,
- visible chunk suppression,
- visible chunk preservation after an internal candidate,
- malformed internal candidate parsing,
- cancellation handling in request runtime,
- duplicate replay prevention,
- TTS-safe segmentation hints,
- TTS execution,
- avatar/Live2D control,
- MEM/SOUL/SLP persistence.

## Next slice

Recommended next implementation boundary:

```text
Phase 5.5-B visible chunk preservation and internal suppression gate
```

That slice should wire an explicit runtime gate and preserve ordinary SSE compatibility while suppressing or blocking internal candidate material after detection.
