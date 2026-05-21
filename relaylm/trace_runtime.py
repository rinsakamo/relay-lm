"""Runtime trace writing helpers for RelayLM MVP-3."""

from __future__ import annotations

from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics
from relaylm.trace import append_trace_record, build_trace_record


def trace_runtime_event(
    *,
    config: RelayLMConfig,
    diagnostics: RequestDiagnostics,
    messages: list[dict[str, Any]],
    response_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Append one runtime trace record when tracing is enabled.

    Returns whether a record was written. Trace writing is intentionally kept
    best-effort by callers so it does not change request handling behavior.
    """

    if not config.trace.enabled or not config.trace.path:
        return False

    record = build_trace_record(
        trace_id=diagnostics.request_id,
        character_id=diagnostics.character_id,
        route_model=diagnostics.route_model,
        mode_applied=diagnostics.mode_applied,
        compiler_used=diagnostics.compiler_used,
        messages=messages,
        response_text=response_text,
        metadata=metadata,
    )
    append_trace_record(config.trace.path, record)
    return True
