"""Runtime SSE wrapper for RelayCTX stream suppression wiring.

Phase 5.5-B2 keeps backend bytes pass-through by default and in dry-run-only
mode. Apply mode performs bounded OpenAI-compatible SSE data-event handling so
RelayCTX internal marker/candidate material does not become user-visible.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from relaylm.relayctx_stream_unpack import (
    RelayCTXStreamSuppressionResult,
    build_relayctx_stream_suppression_node_result,
)
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_CLOSE, RELAYCTX_UPDATE_OPEN

if TYPE_CHECKING:
    from relaylm.pipeline_context import PipelineContext

_INTERNAL_SENTINELS = (RELAYCTX_UPDATE_OPEN, RELAYCTX_UPDATE_CLOSE)
_MAX_SENTINEL_CHARS = max(len(marker) for marker in _INTERNAL_SENTINELS)
_MIN_PARTIAL_SENTINEL_PREFIX_CHARS = 5
_DEFAULT_MAX_BUFFER_CHARS = 256
_SSE_SEPARATORS = (b"\r\n\r\n", b"\n\n")


def wrap_stream_with_relayctx_suppression(
    body_iter: AsyncIterator[bytes],
    *,
    enabled: bool,
    dry_run_only: bool = True,
    max_buffer_chars: int = _DEFAULT_MAX_BUFFER_CHARS,
    pipeline_context: "PipelineContext | None" = None,
) -> AsyncIterator[bytes]:
    """Wrap one backend SSE byte iterator with the RelayCTX stream gate.

    Disabled and dry-run-only modes are byte-for-byte pass-through. Apply mode
    buffers only bounded visible text needed to detect internal sentinels across
    SSE/data chunk boundaries, then suppresses marker/candidate material after
    the first complete or terminal-partial internal marker.
    """

    max_buffer_chars = _normalise_max_buffer_chars(max_buffer_chars)
    if not enabled:
        return _pass_through_stream(
            body_iter,
            enabled=False,
            dry_run_only=dry_run_only,
            max_buffer_chars=max_buffer_chars,
            pipeline_context=pipeline_context,
        )
    if dry_run_only:
        return _dry_run_stream(
            body_iter,
            max_buffer_chars=max_buffer_chars,
            pipeline_context=pipeline_context,
        )
    return _apply_suppression_stream(
        body_iter,
        max_buffer_chars=max_buffer_chars,
        pipeline_context=pipeline_context,
    )


async def _pass_through_stream(
    body_iter: AsyncIterator[bytes],
    *,
    enabled: bool,
    dry_run_only: bool,
    max_buffer_chars: int,
    pipeline_context: "PipelineContext | None",
) -> AsyncIterator[bytes]:
    chunk_count = 0
    try:
        async for chunk in body_iter:
            chunk_count += 1
            yield chunk
    finally:
        _record_result(
            pipeline_context,
            RelayCTXStreamSuppressionResult(
                status="disabled",
                output_chunks=(),
                chunk_count=chunk_count,
                valid_chunk_count=0,
                invalid_chunk_count=0,
                observed_chars=0,
                emitted_chars=0,
                suppressed_chars=0,
                max_buffer_chars=max_buffer_chars,
                enabled=enabled,
                dry_run_only=dry_run_only,
                marker_present=False,
                complete_sentinel_detected=False,
                split_sentinel_detected=False,
                terminal_partial_sentinel=False,
                suppression_applied=False,
                suppression_would_apply=False,
                output_mutated=False,
                blocked_reasons=(),
            ),
        )


async def _dry_run_stream(
    body_iter: AsyncIterator[bytes],
    *,
    max_buffer_chars: int,
    pipeline_context: "PipelineContext | None",
) -> AsyncIterator[bytes]:
    state = _RuntimeSuppressionState(
        enabled=True,
        dry_run_only=True,
        max_buffer_chars=max_buffer_chars,
    )
    frame_buffer = b""
    try:
        async for chunk in body_iter:
            state.chunk_count += 1
            if not isinstance(chunk, bytes):
                state.invalid_chunk_count += 1
                state.reasons.append("non_bytes_stream_chunk")
                yield chunk  # type: ignore[misc]
                continue
            frame_buffer += chunk
            frames, frame_buffer = _split_sse_frames(frame_buffer)
            for frame in frames:
                _observe_frame_for_dry_run(state, frame)
            yield chunk
    except Exception:
        state.invalid_chunk_count += 1
        state.reasons.append("backend_stream_iterator_error")
        raise
    finally:
        if frame_buffer:
            _observe_frame_for_dry_run(state, frame_buffer)
        _record_result(pipeline_context, state.to_result())


async def _apply_suppression_stream(
    body_iter: AsyncIterator[bytes],
    *,
    max_buffer_chars: int,
    pipeline_context: "PipelineContext | None",
) -> AsyncIterator[bytes]:
    state = _RuntimeSuppressionState(
        enabled=True,
        dry_run_only=False,
        max_buffer_chars=max_buffer_chars,
    )
    frame_buffer = b""
    try:
        async for chunk in body_iter:
            state.chunk_count += 1
            if not isinstance(chunk, bytes):
                state.invalid_chunk_count += 1
                state.reasons.append("non_bytes_stream_chunk")
                break
            frame_buffer += chunk
            frames, frame_buffer = _split_sse_frames(frame_buffer)
            for frame in frames:
                for output_frame in _process_frame_for_apply(state, frame):
                    yield output_frame
            if state.invalid_chunk_count:
                break
    except Exception:
        state.invalid_chunk_count += 1
        state.reasons.append("backend_stream_iterator_error")
    else:
        if not state.invalid_chunk_count and frame_buffer:
            for output_frame in _process_frame_for_apply(state, frame_buffer):
                yield output_frame
        if not state.invalid_chunk_count:
            for output_frame in state.flush_pending_at_boundary():
                yield output_frame
    finally:
        _record_result(pipeline_context, state.to_result())


def _observe_frame_for_dry_run(state: "_RuntimeSuppressionState", frame: bytes) -> None:
    try:
        text = frame.decode("utf-8")
    except UnicodeDecodeError:
        state.invalid_chunk_count += 1
        state.reasons.append("stream_chunk_decode_failed")
        return
    payload = _extract_sse_data_payload(text)
    if payload is None or payload == "[DONE]":
        return
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        state.invalid_chunk_count += 1
        state.reasons.append("sse_data_json_invalid")
        return
    for content, _path in _extract_content_fields(data):
        state.observe_content(content)


def _process_frame_for_apply(
    state: "_RuntimeSuppressionState",
    frame: bytes,
) -> list[bytes]:
    try:
        text = frame.decode("utf-8")
    except UnicodeDecodeError:
        state.invalid_chunk_count += 1
        state.reasons.append("stream_chunk_decode_failed")
        return []

    payload = _extract_sse_data_payload(text)
    if payload is None:
        if state.suppression_started:
            return []
        return state.flush_pending_at_boundary() + [frame]
    if payload == "[DONE]":
        return state.flush_pending_at_boundary() + [frame]

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        state.invalid_chunk_count += 1
        state.reasons.append("sse_data_json_invalid")
        return []

    content_fields = _extract_content_fields(data)
    if not content_fields:
        if state.suppression_started:
            return []
        return state.flush_pending_at_boundary() + [frame]
    if len(content_fields) != 1:
        state.invalid_chunk_count += 1
        state.reasons.append("multiple_stream_content_fields")
        return []
    content, path = content_fields[0]
    if state.suppression_started:
        state.observe_content(content)
        return []
    return state.process_content(data, path, content)


class _RuntimeSuppressionState:
    def __init__(
        self,
        *,
        enabled: bool,
        dry_run_only: bool,
        max_buffer_chars: int,
    ) -> None:
        self.enabled = enabled
        self.dry_run_only = dry_run_only
        self.max_buffer_chars = max_buffer_chars
        self.chunk_count = 0
        self.valid_chunk_count = 0
        self.invalid_chunk_count = 0
        self.observed_chars = 0
        self.emitted_chars = 0
        self.retained = ""
        self.pending_visible = ""
        self.pending_template: dict[str, Any] | None = None
        self.pending_path: tuple[Any, ...] | None = None
        self.complete_sentinel_detected = False
        self.split_sentinel_detected = False
        self.terminal_partial_sentinel = False
        self.suppression_started = False
        self.reasons: list[str] = []

    def observe_content(self, content: str) -> None:
        self.valid_chunk_count += 1
        self.observed_chars += len(content)
        previous_tail = self.retained[-(_MAX_SENTINEL_CHARS - 1) :]
        boundary_text = previous_tail + content
        chunk_has_complete = any(marker in content for marker in _INTERNAL_SENTINELS)
        boundary_has_complete = any(
            marker in boundary_text for marker in _INTERNAL_SENTINELS
        )
        if chunk_has_complete or boundary_has_complete:
            self.complete_sentinel_detected = True
            self.reasons.append("internal_sentinel_detected")
        if boundary_has_complete and not chunk_has_complete:
            self.split_sentinel_detected = True
            self.reasons.append("split_internal_sentinel_detected")
        self.retained = (self.retained + content)[-self.max_buffer_chars :]
        if _terminal_partial_prefix_index(self.retained) is not None:
            self.terminal_partial_sentinel = True
            self.reasons.append("partial_internal_sentinel_prefix")
        else:
            self.terminal_partial_sentinel = False

    def process_content(
        self,
        template: dict[str, Any],
        path: tuple[Any, ...],
        content: str,
    ) -> list[bytes]:
        self.observe_content(content)
        self.pending_template = template
        self.pending_path = path
        self.pending_visible += content

        sentinel_index = _first_sentinel_index(self.pending_visible)
        if sentinel_index is not None:
            safe_text = self.pending_visible[:sentinel_index]
            self.pending_visible = ""
            self.suppression_started = True
            if safe_text:
                return [self.render_content_frame(safe_text)]
            return []

        partial_index = _terminal_partial_prefix_index(self.pending_visible)
        if partial_index is not None:
            safe_text = self.pending_visible[:partial_index]
            self.pending_visible = self.pending_visible[partial_index:]
            if safe_text:
                return [self.render_content_frame(safe_text)]
            return []

        keep_tail_chars = _MAX_SENTINEL_CHARS - 1
        if len(self.pending_visible) <= keep_tail_chars:
            return []
        safe_text = self.pending_visible[:-keep_tail_chars]
        self.pending_visible = self.pending_visible[-keep_tail_chars:]
        if safe_text:
            return [self.render_content_frame(safe_text)]
        return []

    def flush_pending_at_boundary(self) -> list[bytes]:
        if not self.pending_visible:
            return []
        partial_index = _terminal_partial_prefix_index(self.pending_visible)
        if partial_index is not None:
            safe_text = self.pending_visible[:partial_index]
            self.pending_visible = ""
            self.terminal_partial_sentinel = True
            self.suppression_started = True
            self.reasons.append("partial_internal_sentinel_prefix")
            if safe_text:
                return [self.render_content_frame(safe_text)]
            return []
        safe_text = self.pending_visible
        self.pending_visible = ""
        if safe_text:
            return [self.render_content_frame(safe_text)]
        return []

    def render_content_frame(self, content: str) -> bytes:
        self.emitted_chars += len(content)
        if self.pending_template is None or self.pending_path is None:
            return b""
        data = deepcopy(self.pending_template)
        _set_path(data, self.pending_path, content)
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return f"data: {payload}\n\n".encode("utf-8")

    def to_result(self) -> RelayCTXStreamSuppressionResult:
        marker_present = self.complete_sentinel_detected or self.terminal_partial_sentinel
        suppression_would_apply = marker_present or self.split_sentinel_detected
        if self.invalid_chunk_count:
            status = "invalid_input"
            suppression_applied = False
            output_mutated = True
        elif self.dry_run_only:
            status = "dry_run_suppression_candidate" if suppression_would_apply else "dry_run_clean"
            suppression_applied = False
            output_mutated = False
        elif self.suppression_started and self.terminal_partial_sentinel and not self.complete_sentinel_detected:
            status = "partial_blocked"
            suppression_applied = True
            output_mutated = True
        elif self.suppression_started:
            status = "suppressed"
            suppression_applied = True
            output_mutated = True
        else:
            status = "clean"
            suppression_applied = False
            output_mutated = False
        suppressed_chars = max(0, self.observed_chars - self.emitted_chars)
        return RelayCTXStreamSuppressionResult(
            status=status,
            output_chunks=(),
            chunk_count=self.chunk_count,
            valid_chunk_count=self.valid_chunk_count,
            invalid_chunk_count=self.invalid_chunk_count,
            observed_chars=self.observed_chars,
            emitted_chars=self.emitted_chars,
            suppressed_chars=suppressed_chars,
            max_buffer_chars=self.max_buffer_chars,
            enabled=self.enabled,
            dry_run_only=self.dry_run_only,
            marker_present=marker_present,
            complete_sentinel_detected=self.complete_sentinel_detected,
            split_sentinel_detected=self.split_sentinel_detected,
            terminal_partial_sentinel=self.terminal_partial_sentinel,
            suppression_applied=suppression_applied,
            suppression_would_apply=suppression_would_apply,
            output_mutated=output_mutated,
            blocked_reasons=_dedupe(self.reasons),
        )


def _split_sse_frames(buffer: bytes) -> tuple[list[bytes], bytes]:
    frames: list[bytes] = []
    rest = buffer
    while True:
        match = _first_separator(rest)
        if match is None:
            return frames, rest
        index, separator = match
        end_index = index + len(separator)
        frames.append(rest[:end_index])
        rest = rest[end_index:]


def _first_separator(buffer: bytes) -> tuple[int, bytes] | None:
    matches = [
        (index, separator)
        for separator in _SSE_SEPARATORS
        if (index := buffer.find(separator)) >= 0
    ]
    if not matches:
        return None
    return min(matches, key=lambda item: item[0])


def _extract_sse_data_payload(event_text: str) -> str | None:
    data_lines: list[str] = []
    for line in event_text.replace("\r\n", "\n").split("\n"):
        if not line.startswith("data:"):
            continue
        value = line[5:]
        if value.startswith(" "):
            value = value[1:]
        data_lines.append(value)
    if not data_lines:
        return None
    return "\n".join(data_lines)


def _extract_content_fields(data: Any) -> list[tuple[str, tuple[Any, ...]]]:
    if not isinstance(data, dict):
        return []
    choices = data.get("choices")
    if not isinstance(choices, list):
        return []
    fields: list[tuple[str, tuple[Any, ...]]] = []
    for choice_index, choice in enumerate(choices):
        if not isinstance(choice, dict):
            continue
        delta = choice.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            fields.append(
                (delta["content"], ("choices", choice_index, "delta", "content"))
            )
        if isinstance(choice.get("text"), str):
            fields.append((choice["text"], ("choices", choice_index, "text")))
    return fields


def _set_path(data: Any, path: tuple[Any, ...], value: str) -> None:
    current = data
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value


def _first_sentinel_index(text: str) -> int | None:
    indexes = [text.find(marker) for marker in _INTERNAL_SENTINELS]
    found = [index for index in indexes if index >= 0]
    return min(found) if found else None


def _terminal_partial_prefix_index(text: str) -> int | None:
    if not text:
        return None
    max_prefix_len = min(len(text), _MAX_SENTINEL_CHARS - 1)
    for marker in _INTERNAL_SENTINELS:
        upper = min(max_prefix_len, len(marker) - 1)
        for prefix_len in range(upper, _MIN_PARTIAL_SENTINEL_PREFIX_CHARS - 1, -1):
            if text.endswith(marker[:prefix_len]):
                return len(text) - prefix_len
    return None


def _normalise_max_buffer_chars(value: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < _MAX_SENTINEL_CHARS
    ):
        return _DEFAULT_MAX_BUFFER_CHARS
    return value


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)


def _record_result(
    pipeline_context: "PipelineContext | None",
    result: RelayCTXStreamSuppressionResult,
) -> None:
    if pipeline_context is None:
        return
    pipeline_context.record_node_result(
        build_relayctx_stream_suppression_node_result(result)
    )
