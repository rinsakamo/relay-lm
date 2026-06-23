"""Post-response Phase 6 I1-B runtime finalization.

The stream observer is byte-preserving and sits outside RelayCTX suppression and
TTS handoff.  The background function runs only after Starlette has completed
response delivery.  It catches all failures, records only content-free node
results, and never changes the already-finalized response.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics
from relaylm.pipeline_context import PipelineContext
from relaylm.relaymem_slp_finalized_turn_source import (
    RelayMEMSLPFinalizedTurnSourceResult,
    build_relaymem_slp_finalized_turn_source,
    build_relaymem_slp_finalized_turn_source_node_result,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_runtime_enqueue import (
    RelayMEMSLPRuntimeEnqueueResult,
    apply_relaymem_slp_runtime_enqueue,
    build_relaymem_slp_runtime_enqueue_failure_result,
    build_relaymem_slp_runtime_enqueue_node_result,
)
from relaylm.trace_runtime import trace_runtime_event

_MAX_VISIBLE_CHARS = 32_768
_SSE_SEPARATORS = (b"\r\n\r\n", b"\n\n")


@dataclass(repr=False)
class RelayMEMSLPFinalizedVisibleTextCapture:
    """Bounded request-local owner for safe visible stream text."""

    max_chars: int = _MAX_VISIBLE_CHARS
    _parts: list[str] = field(default_factory=list, init=False, repr=False)
    _char_count: int = field(default=0, init=False, repr=False)
    _finalized: bool = field(default=False, init=False, repr=False)
    _invalid: bool = field(default=False, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.max_chars) is not int or self.max_chars < 1:
            raise ValueError("stream_capture_max_chars_invalid")

    def __repr__(self) -> str:
        with self._lock:
            return (
                "RelayMEMSLPFinalizedVisibleTextCapture("
                f"finalized={self._finalized}, invalid={self._invalid}, "
                "content_omitted=True)"
            )

    def append(self, value: object) -> None:
        with self._lock:
            if self._finalized or self._invalid:
                return
            if type(value) is not str:
                self._invalidate_locked()
                return
            next_count = self._char_count + len(value)
            if next_count > self.max_chars:
                self._invalidate_locked()
                return
            self._parts.append(value)
            self._char_count = next_count

    def invalidate(self) -> None:
        with self._lock:
            self._invalidate_locked()

    def finalize(self) -> None:
        with self._lock:
            self._finalized = True

    def finalized_text(self) -> str | None:
        with self._lock:
            if not self._finalized or self._invalid:
                return None
            value = "".join(self._parts)
            return value if value else None

    def _invalidate_locked(self) -> None:
        self._invalid = True
        self._parts.clear()
        self._char_count = 0


def wrap_stream_with_relaymem_slp_finalized_turn_capture(
    body_iter: AsyncIterator[bytes],
    *,
    capture: RelayMEMSLPFinalizedVisibleTextCapture,
) -> AsyncIterator[bytes]:
    """Observe final safe OpenAI-compatible SSE without changing any byte."""

    if type(capture) is not RelayMEMSLPFinalizedVisibleTextCapture:
        raise TypeError("exact_stream_capture_required")
    return _observe(body_iter, capture)


async def _observe(
    body_iter: AsyncIterator[bytes],
    capture: RelayMEMSLPFinalizedVisibleTextCapture,
) -> AsyncIterator[bytes]:
    frame_buffer = b""
    try:
        async for chunk in body_iter:
            yield chunk
            if type(chunk) is not bytes:
                capture.invalidate()
                continue
            frame_buffer += chunk
            frames, frame_buffer = _split_sse_frames(frame_buffer)
            for frame in frames:
                _observe_frame(frame, capture)
    except BaseException:
        capture.invalidate()
        raise
    finally:
        if frame_buffer:
            _observe_frame(frame_buffer, capture)
        capture.finalize()


def run_relaymem_slp_runtime_enqueue_after_response(
    *,
    config: RelayLMConfig,
    diagnostics: RequestDiagnostics,
    pipeline_context: PipelineContext,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry,
    status_code: int,
    resolved_session_id: str | None,
    relayscn_scene_policy_artifact: dict[str, Any],
    relayemo_artifact: dict[str, Any] | None,
    assistant_visible_text: str | None = None,
    stream_capture: RelayMEMSLPFinalizedVisibleTextCapture | None = None,
    message_count: int = 0,
) -> RelayMEMSLPRuntimeEnqueueResult:
    """Run safe source capture/enqueue after response delivery and swallow errors."""

    source_result: RelayMEMSLPFinalizedTurnSourceResult | None = None
    try:
        visible_text: object = assistant_visible_text
        if stream_capture is not None:
            if type(stream_capture) is not RelayMEMSLPFinalizedVisibleTextCapture:
                raise TypeError("exact_stream_capture_required")
            visible_text = stream_capture.finalized_text()
        source_result = build_relaymem_slp_finalized_turn_source(
            pipeline_context,
            assistant_visible_text=visible_text,
            status_code=status_code,
            resolved_session_id=resolved_session_id,
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayemo_artifact=relayemo_artifact,
            response_finalized=True,
            enabled=config.relaymem_slp_runtime_enqueue_enabled,
        )
        result = apply_relaymem_slp_runtime_enqueue(
            source_result,
            registry=registry,
            queue_root=config.relaymem_slp_queue_root,
            enabled=config.relaymem_slp_runtime_enqueue_enabled,
            dry_run_only=config.relaymem_slp_runtime_enqueue_dry_run_only,
            apply_enabled=config.relaymem_slp_runtime_enqueue_apply_enabled,
        )
    except BaseException:
        result = build_relaymem_slp_runtime_enqueue_failure_result()

    nodes = []
    try:
        if source_result is not None:
            nodes.append(build_relaymem_slp_finalized_turn_source_node_result(source_result))
        nodes.append(build_relaymem_slp_runtime_enqueue_node_result(result))
        for node in nodes:
            pipeline_context.record_node_result(node)
        trace_runtime_event(
            config=config,
            diagnostics=diagnostics,
            message_count=message_count,
            response_present=True,
            metadata={"event": "relaymem_slp_runtime_enqueue"},
            pipeline_node_results=tuple(nodes),
        )
    except BaseException:
        pass
    finally:
        if result.status == "dry_run_ready" and result.source_scope is not None:
            result.source_scope.close()
    return result


def _observe_frame(
    frame: bytes,
    capture: RelayMEMSLPFinalizedVisibleTextCapture,
) -> None:
    try:
        text = frame.decode("utf-8")
    except UnicodeDecodeError:
        capture.invalidate()
        return
    payload = _extract_sse_data_payload(text)
    if payload is None or payload == "[DONE]":
        return
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        capture.invalidate()
        return
    fields = _extract_content_fields(data)
    if len(fields) > 1:
        capture.invalidate()
        return
    if fields:
        capture.append(fields[0])


def _split_sse_frames(buffer: bytes) -> tuple[list[bytes], bytes]:
    frames: list[bytes] = []
    rest = buffer
    while True:
        matches = [
            (index, separator)
            for separator in _SSE_SEPARATORS
            if (index := rest.find(separator)) >= 0
        ]
        if not matches:
            return frames, rest
        index, separator = min(matches, key=lambda item: item[0])
        end = index + len(separator)
        frames.append(rest[:end])
        rest = rest[end:]


def _extract_sse_data_payload(event_text: str) -> str | None:
    data_lines: list[str] = []
    for line in event_text.replace("\r\n", "\n").split("\n"):
        if not line.startswith("data:"):
            continue
        value = line[5:]
        if value.startswith(" "):
            value = value[1:]
        data_lines.append(value)
    return "\n".join(data_lines) if data_lines else None


def _extract_content_fields(data: object) -> list[str]:
    if type(data) is not dict:
        return []
    choices = data.get("choices")
    if type(choices) is not list:
        return []
    fields: list[str] = []
    for choice in choices:
        if type(choice) is not dict:
            continue
        delta = choice.get("delta")
        if type(delta) is dict and type(delta.get("content")) is str:
            fields.append(delta["content"])
        if type(choice.get("text")) is str:
            fields.append(choice["text"])
    return fields


__all__ = [
    "RelayMEMSLPFinalizedVisibleTextCapture",
    "run_relaymem_slp_runtime_enqueue_after_response",
    "wrap_stream_with_relaymem_slp_finalized_turn_capture",
]
