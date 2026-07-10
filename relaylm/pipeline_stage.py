"""Tiny pipeline stage runner for RelayLM's managed chat completion handler.

This module owns the timing bracket (``started_at``/``completed_at``/
``duration_ms``) that ``handle_managed_chat_completion`` previously
hand-rolled around each pipeline stage via a
``x_started_at, x_start_monotonic = _start_timing()`` /
``node_timings["x"] = _finalize_timing(...)`` pair. ``run_stage`` collapses
that boilerplate into a single call while recording byte-for-byte the same
``node_timings`` entry shape.

This is intentionally small: no stage registry, no config, no retries, no
framework ambitions. It is a call wrapper, nothing more. Stage bodies stay in
``managed_chat_runtime.py`` (or wherever later PRs move them); this module
only brackets whichever callable is handed to it.

Conditional stages (e.g. RelayEMO, which only runs -- and only records a
``node_timings`` entry -- when ``config.relayemo_enabled`` is set) remain
expressible unchanged: callers simply choose not to call ``run_stage`` for a
stage that isn't running today. ``run_stage`` never forces a timing entry to
exist; it only ever writes one when it is actually invoked.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import inspect
import time
from typing import Any, Awaitable, Callable, TypeVar, cast

_T = TypeVar("_T")


def _start_timing() -> tuple[str, float]:
    """Capture a node's start for LAT-1 RelayRUN timing (measurement only)."""

    return datetime.now(timezone.utc).isoformat(), time.monotonic()


def _finalize_timing(started_at: str, start_monotonic: float) -> dict[str, Any]:
    """Finish a node timing bracket started by ``_start_timing``.

    Wall-clock ISO timestamps are recorded for ``started_at``/``completed_at``;
    ``duration_ms`` is derived from a monotonic clock so it stays accurate even
    if the wall clock is adjusted mid-request.
    """

    return {
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": max(0, round((time.monotonic() - start_monotonic) * 1000)),
    }


async def run_stage(
    node_timings: dict[str, dict[str, Any] | None],
    name: str,
    fn: Callable[..., _T | Awaitable[_T]],
    /,
    *args: Any,
    offload: bool = False,
    **kwargs: Any,
) -> _T:
    """Run one pipeline stage, recording its timing into ``node_timings[name]``.

    Sync and async callables are supported when ``offload`` is false. Pass
    ``offload=True`` only for a blocking synchronous callable; async callables
    are rejected because moving coroutine creation to a worker thread does not
    execute or await the coroutine there.

    The timing entry is written only after the stage completes successfully, so
    exceptions and invalid offload usage do not create a misleading completed
    node timing.
    """

    started_at, start_monotonic = _start_timing()
    if offload:
        if inspect.iscoroutinefunction(fn):
            raise TypeError("offload=True requires a synchronous callable")
        result = await asyncio.to_thread(fn, *args, **kwargs)
        if inspect.isawaitable(result):
            close = getattr(result, "close", None)
            if callable(close):
                close()
            raise TypeError("offload=True callable must not return an awaitable")
    else:
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result

    node_timings[name] = _finalize_timing(started_at, start_monotonic)
    return cast(_T, result)
