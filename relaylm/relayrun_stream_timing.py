"""LAT-2 stream perceived-latency measurement (``relayrun.stream_timing.v0``).

Measures a streaming response's perceived latency -- time to first chunk,
stream drain time, chunk count -- without inspecting chunk content, changing
SSE payload bytes/ordering, buffering, or delaying delivery to the client.
This is a separate trace from LAT-1's ``timing_summary`` (whose
``time_to_first_token_ms`` stays ``null`` for streaming responses because the
RelayRUN checkpoint is built before the stream starts sending bytes -- see
``docs/architecture/lat1_latency_measurement.md``). See
``docs/architecture/lat2_mobile_perceived_latency.md`` for the full design.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.trace import append_trace_record, build_trace_record

STREAM_TIMING_SCHEMA_VERSION = "relayrun.stream_timing.v0"

# The only reason ids this module ever emits. A wrapper that only observes
# bytes passing through an async generator cannot reliably distinguish a
# client disconnect from an explicit generator close (both surface as
# GeneratorExit at this layer) or detect a malformed stream without parsing
# chunk content, so those are intentionally not separate reason ids here.
STREAM_TIMING_ERROR_REASON_IDS: frozenset[str] = frozenset(
    {"generator_close", "stream_cancelled", "backend_stream_error"}
)

StreamTimingFinalizeCallback = Callable[[dict[str, Any]], None]


def _non_negative_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def build_relayrun_stream_timing(
    *,
    stream_open_ms: int | None,
    time_to_first_chunk_ms: int | None,
    stream_drain_ms: int | None,
    stream_chunk_count: int,
    stream_completed: bool,
    stream_error_reason_id: str | None,
) -> dict[str, Any]:
    """Build the content-free, numeric-only LAT-2 stream timing artifact.

    Pure aggregation over already-measured values -- no timing or I/O of its
    own. Never carries chunk bytes, prompt text, or response body text.
    """

    resolved_reason_id = (
        stream_error_reason_id
        if stream_error_reason_id in STREAM_TIMING_ERROR_REASON_IDS
        else None
    )
    return {
        "schema_version": STREAM_TIMING_SCHEMA_VERSION,
        "content_free": True,
        "stream": True,
        "stream_open_ms": _non_negative_int_or_none(stream_open_ms),
        "time_to_first_chunk_ms": _non_negative_int_or_none(time_to_first_chunk_ms),
        "stream_drain_ms": _non_negative_int_or_none(stream_drain_ms),
        "stream_chunk_count": (
            stream_chunk_count
            if isinstance(stream_chunk_count, int)
            and not isinstance(stream_chunk_count, bool)
            and stream_chunk_count >= 0
            else 0
        ),
        "stream_completed": bool(stream_completed),
        "stream_error_reason_id": resolved_reason_id,
        "raw_chunk_included": False,
        "prompt_included": False,
        "response_body_included": False,
    }


async def wrap_stream_with_relayrun_stream_timing(
    body_iter: AsyncIterator[bytes],
    *,
    stream_open_start_monotonic: float,
    stream_open_ms: int | None,
    on_finalize: StreamTimingFinalizeCallback | None = None,
) -> AsyncIterator[bytes]:
    """Pass through stream bytes unchanged while measuring perceived latency.

    Every chunk is yielded to the caller immediately; timing bookkeeping for
    a chunk happens before the yield (so the "first chunk" timestamp reflects
    when the chunk became available to send) and is otherwise O(1) per
    chunk. Chunk bytes are never inspected, decoded, or retained -- only
    counted and timestamped.
    """

    chunk_count = 0
    first_chunk_monotonic: float | None = None
    completed = False
    error_reason_id: str | None = None
    try:
        async for chunk in body_iter:
            now = time.monotonic()
            if first_chunk_monotonic is None:
                first_chunk_monotonic = now
            chunk_count += 1
            yield chunk
        completed = True
    except asyncio.CancelledError:
        error_reason_id = "stream_cancelled"
        raise
    except GeneratorExit:
        error_reason_id = "generator_close"
        raise
    except Exception:
        error_reason_id = "backend_stream_error"
        raise
    finally:
        drain_monotonic = time.monotonic()
        time_to_first_chunk_ms = (
            max(0, round((first_chunk_monotonic - stream_open_start_monotonic) * 1000))
            if first_chunk_monotonic is not None
            else None
        )
        stream_drain_ms = max(
            0, round((drain_monotonic - stream_open_start_monotonic) * 1000)
        )
        artifact = build_relayrun_stream_timing(
            stream_open_ms=stream_open_ms,
            time_to_first_chunk_ms=time_to_first_chunk_ms,
            stream_drain_ms=stream_drain_ms,
            stream_chunk_count=chunk_count,
            stream_completed=completed,
            stream_error_reason_id=error_reason_id,
        )
        if on_finalize is not None:
            try:
                on_finalize(artifact)
            except Exception:
                pass


def emit_relayrun_stream_timing_trace(
    *,
    config: RelayLMConfig,
    request_id: str,
    character_id: str | None,
    route_model: str | None,
    mode_applied: str | None,
    stream_timing: Mapping[str, Any],
) -> bool:
    """Append one content-free LAT-2 stream-timing trace record.

    Independent of ``relaylm.trace_runtime``'s TTS-only stream-final state
    machine, so it always emits regardless of which route flags are enabled.
    Never raises: a trace failure must not affect the already-sent stream.
    """

    if not config.trace.enabled or not config.trace.path:
        return False
    try:
        record = build_trace_record(
            trace_id=request_id,
            request_id=request_id,
            character_id=character_id,
            route_model=route_model,
            mode_applied=mode_applied,
            compiler_used=False,
            message_count=0,
            response_present=False,
            metadata={
                "event": "backend_stream_response",
                "stream_timing": dict(stream_timing),
            },
        )
        append_trace_record(config.trace.path, record)
    except Exception:
        return False
    return True
