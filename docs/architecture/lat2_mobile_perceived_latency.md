---
relaylm_doc_type: implementation_handoff
relaylm_authority: lat2_mobile_perceived_latency_boundary_scope
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - the stream_timing schema changes
  - the wrapping point around body_iter in relaylm/managed_chat_runtime.py moves
  - LAT-1's timing_summary.time_to_first_token_ms limitation is resolved and this slice is folded back in
relaylm_not_authoritative_for:
  - search algorithm, ranking, or candidate-limit (K) design decisions
  - degradation ladder, timeout, or node-skip design
  - SSE payload/backend-forwarding behavior
  - repository-wide current implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
---

# LAT-2 Mobile Perceived Latency

## Summary

LAT-2 adds a content-free `relayrun.stream_timing.v0` trace that measures a
streaming response's *perceived* latency -- time to first chunk, stream
drain time, and chunk count -- for mobile dogfooding. It is measurement
only: no search algorithm, ranking, candidate-limit, skip/degrade, timeout,
backend-forwarding, SSE payload, or UI behavior changed. See
[LAT-1 Latency Measurement](lat1_latency_measurement.md) for the RelayRUN
per-node timing and `timing_summary` foundation this builds on, and its
"Known limitation" section for why `time_to_first_token_ms` cannot be filled
in from the request-path checkpoint.

## Why this is a separate trace from LAT-1's `timing_summary`

The RelayRUN checkpoint artifact (including `timing_summary`) is fully built
and attached to response headers *before* a streaming response begins
sending bytes to the client (`relaylm/managed_chat_runtime.py` builds
`stream_relayrun_artifact` and calls `stream_diagnostics.to_headers()`
before `StreamingResponse` starts iterating `body_iter`). Filling in
`timing_summary.time_to_first_token_ms` synchronously would require either
delaying the response until the first chunk arrives (a behavior change) or
mutating an already-sent headers artifact (not possible). LAT-2 does
neither: it wraps the stream generator and records a **second, later**
content-free trace record once the stream finishes (or errors), reusing the
"stream-final trace" pattern already used by Phase 5.5-C2/C4's TTS handoff
(`docs/architecture/phase55b1_stream_suppression_gate_handoff.md`,
`relaylm/relayctx_tts_adapter_handoff_runtime.py`) -- but as an independent
emission path, not by extending that TTS-specific state machine (see
"Independent of the TTS stream-final mechanism" below).

`timing_summary.time_to_first_token_ms` itself is **not** touched by this
slice: it stays `null` for every request, exactly as LAT-1 left it.

## Implemented files

```text
relaylm/relayrun_stream_timing.py   STREAM_TIMING_SCHEMA_VERSION;
                                     build_relayrun_stream_timing();
                                     wrap_stream_with_relayrun_stream_timing();
                                     emit_relayrun_stream_timing_trace()
relaylm/managed_chat_runtime.py     body_iter wrapped with the LAT-2 timing
                                     observer (only when config.trace.enabled)
                                     immediately before StreamingResponse is
                                     constructed, after every other stream
                                     wrapper has already been applied
relaylm/audit_projection.py         _RELAYRUN_STREAM_TIMING validator;
                                     "stream_timing" added to the top-level
                                     content-free projection whitelist
scripts/relaylm_lat2_stream_timing_smoke.py            wrapper + full-request smoke
scripts/relaylm_lat2_stream_timing_security_smoke.py   content-free smoke
```

## What is measured

`relaylm.relayrun_stream_timing.wrap_stream_with_relayrun_stream_timing`
wraps the already-fully-assembled `body_iter` (after suppression/TTS-handoff
wrapping, after the RelayMEM SLP finalized-turn capture wrap) as the
outermost layer, immediately before it is handed to `StreamingResponse`.
It never buffers, reorders, decodes, or delays a chunk -- each chunk is
timestamped and counted, then `yield`ed immediately, so client delivery
timing is unaffected.

| field | meaning |
|---|---|
| `stream_open_ms` | time from starting the backend stream open call to receiving status/headers -- the same value LAT-1 records as `backend_forward_ms` for a streaming request, carried over so a single record has both |
| `time_to_first_chunk_ms` | time from the same stream-open start until the first body chunk is ready to send to the client |
| `stream_drain_ms` | time from the same stream-open start until the wrapped generator finishes (normally or via error/close) |
| `stream_chunk_count` | number of body chunks observed, content never inspected |
| `stream_completed` | `true` only if the upstream iterator was exhausted normally |
| `stream_error_reason_id` | one of the fixed reason ids below, or `null` |

All fields are numeric, boolean, `null`, or the fixed `schema_version`
string -- content-free by construction, matching LAT-1's
`timing_summary` shape discipline.

## Error handling: fixed `stream_error_reason_id` set only

A wrapper that only observes bytes passing through an async generator
cannot reliably distinguish every failure mode the original prompt
considered (client disconnect, backend stream error, malformed stream,
cancellation, generator close) without either parsing chunk content (which
LAT-2 deliberately avoids to stay content-free and minimal) or having
ASGI-level visibility this wrapper does not have. What is actually
detectable at this layer, and the only three reason ids ever emitted:

| reason id | raised as |
|---|---|
| `generator_close` | `GeneratorExit` -- covers both an explicit close and Starlette calling `body_iterator.aclose()` on client disconnect; this layer cannot distinguish the two |
| `stream_cancelled` | `asyncio.CancelledError` |
| `backend_stream_error` | any other exception raised while iterating the backend stream |

"Malformed stream" is not a separate reason id: detecting it would require
parsing SSE frame/JSON content, which this wrapper does not do. In every
case the wrapper re-raises the original exception unchanged after recording
the fixed reason id -- it never swallows or replaces upstream errors, and
never logs the raw exception text, message, or class name.

## Recorded as a second `backend_stream_response` trace record

`relaylm.relayrun_stream_timing.emit_relayrun_stream_timing_trace` appends
one additional content-free trace record (same `event: backend_stream_response`
value as the existing headers-time record, same `request_id`) once the
wrapped generator's `finally` block runs. It is only emitted when
`config.trace.enabled` and `config.trace.path` are set -- when tracing is
disabled, the wrapper is not even applied to `body_iter`, so there is no
per-chunk timing overhead in that configuration, mirroring the "avoid trace
diagnostics work when tracing is disabled" discipline already applied to
`relaylm/trace_runtime.py`. Non-streaming requests never produce a
`stream_timing` record at all -- LAT-1's non-stream `timing_summary`
behavior is unchanged.

`request_id` (present as `request_id`/`trace_id` on every trace record
already, by the existing `relaylm.trace.TraceRecord` shape) is the
correlation key between the headers-time record and this stream-final
record; no new identifier is introduced. This matches every other trace
record already written by this codebase and does not change the existing
request-id-in-trace exposure surface.

### Independent of the TTS stream-final mechanism

`relaylm.trace_runtime.trace_runtime_stream_final_pipeline_node_results`
exists for exactly this "append a later record once a stream finishes"
need, but it is scoped tightly to Phase 5.5-C2/C4 TTS node results
(`_is_stream_final_tts_node_results` only accepts three specific TTS node
names, and the whole mechanism only activates when C2/B2 route flags are
enabled). Reusing it for LAT-2 would make stream-timing measurement depend
on TTS-handoff configuration, which is unrelated. LAT-2 instead calls
`relaylm.trace.build_trace_record` / `append_trace_record` directly --
the same content-free-projecting primitives `trace_runtime_event` itself
uses -- so it always emits for every streaming request regardless of which
other route flags are set.

## Non-goals

- No latency optimization, response-time guarantee, or SLA.
- No search algorithm, ranking, or candidate-limit (K) change.
- No SSE payload, chunk ordering, or backend-forwarding change.
- No response buffering (chunks are yielded before their own timing
  bookkeeping completes).
- No token counting or real tokenizer -- `stream_chunk_count` counts SSE
  body chunks, not tokens.
- No UI display of these numbers (see
  `docs/evaluation/mobile_dogfood_observation_runbook.md` for how an
  operator reads them from the trace by hand).
- No Cloudflare/mobile-network-level measurement or browser Navigation
  Timing integration.
- No timeout/degradation-ladder change, no O2/O3 change, no TTS/avatar
  timing change.
- `timing_summary.time_to_first_token_ms` is still `null` for every
  request -- this slice does not fill it in.

## Smoke coverage

- `scripts/relaylm_lat2_stream_timing_smoke.py` -- wrapper unit checks
  (byte-exact passthrough and ordering, non-negative timing, correct chunk
  count, upstream-exception and early-`aclose()` error paths); a
  full-request check against a fake streaming backend that the persisted
  trace's second `backend_stream_response` record carries a numeric
  `stream_timing`; a full non-streaming request confirming LAT-1's
  behavior is untouched (`timing_summary` present, no `stream_timing` key).
- `scripts/relaylm_lat2_stream_timing_security_smoke.py` -- the builder
  only ever emits the fixed key set; the content-free audit projector
  drops forged/unsupported `stream_timing` fields and non-enum
  `stream_error_reason_id` values; a full request whose prompt, response,
  and forged secret-shaped/path-shaped chunks act as canaries never leaks
  them into the persisted trace; a mid-stream backend error records only
  the fixed `backend_stream_error` reason id, never the raw exception text.
