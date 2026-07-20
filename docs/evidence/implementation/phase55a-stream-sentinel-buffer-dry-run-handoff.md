---
relaylm_doc_type: evidence
relaylm_authority: phase55a_stream_sentinel_buffer_dry_run_implementation_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current runtime behavior
  - canonical Stream Unpack architecture
  - future Stream Unpack apply behavior
  - TTS execution
  - RelaySOUL persistence
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/phase5_5_stream_unpack_bounded_slice.md
relaylm_source_commit: c0135a9547ef2eda6d58bf87a274cc009239b8aa
relaylm_source_pr: 311
relaylm_recorded_on: 2026-06-20
relaylm_source_blob: 95481903cd5cb43bc2444a8647fd44b919f7d9e7
relaylm_source_content_sha256: d46295251db3365fef805056a192278674ec09b043ace4bfec672b0dcedf8a5b
relaylm_pre_cutover_blob: 95481903cd5cb43bc2444a8647fd44b919f7d9e7
relaylm_pre_cutover_content_sha256: d46295251db3365fef805056a192278674ec09b043ace4bfec672b0dcedf8a5b
---
# Phase 5.5-A Stream Sentinel Buffer Dry-Run Evidence

This frozen record preserves the bounded implementation handoff merged by PR #311 on 2026-06-20. The statements below describe that source-time Phase 5.5-A slice; current Stream Unpack architecture and runtime status remain owned by [Phase 5.5 Stream Unpack Bounded Slice](../../architecture/phase5_5_stream_unpack_bounded_slice.md), [Project Status](../../PROJECT_STATUS.md), and the implementation.

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
