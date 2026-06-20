"""Runtime wiring for RelayCTX TTS adapter handoff planning.

Phase 5.5-C2 consumes only safe visible SSE output after Phase 5.5-B2
suppression apply mode. It records C0/C1 content-free node results and does
not mutate stream bytes, execute TTS, generate audio, control avatars, or
persist CTX/MEM/SOUL/SLP state.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from relaylm.relayctx_tts_adapter_handoff import (
    build_relayctx_tts_adapter_handoff_node_result,
    build_tts_adapter_handoff_plan,
)
from relaylm.relayctx_tts_segmentation import (
    build_relayctx_tts_segmentation_node_result,
    build_tts_safe_segmentation_hints,
)

if TYPE_CHECKING:
    from relaylm.pipeline_context import PipelineContext

_SSE_SEPARATORS = (b"\r\n\r\n", b"\n\n")
_DEFAULT_MAX_SEGMENT_CHARS = 120
_DEFAULT_MIN_SEGMENT_CHARS = 8


def wrap_stream_with_tts_adapter_handoff(
    body_iter: AsyncIterator[bytes],
    *,
    enabled: bool,
    dry_run_only: bool = True,
    b2_safe_visible_output_available: bool,
    max_segment_chars: int = _DEFAULT_MAX_SEGMENT_CHARS,
    min_segment_chars: int = _DEFAULT_MIN_SEGMENT_CHARS,
    pipeline_context: "PipelineContext | None" = None,
) -> AsyncIterator[bytes]:
    """Pass through SSE bytes while planning runtime-private TTS handoff.

    The wrapper observes bytes only when C2 is enabled and the upstream B2
    runtime suppression wrapper is in apply mode. That precondition ensures the
    observed content is the same safe visible output that is user-visible after
    internal RelayCTX material has been suppressed.
    """

    if not enabled or not b2_safe_visible_output_available:
        return _pass_through_stream(body_iter)
    return _observe_safe_visible_output_stream(
        body_iter,
        dry_run_only=dry_run_only,
        max_segment_chars=max_segment_chars,
        min_segment_chars=min_segment_chars,
        pipeline_context=pipeline_context,
    )


async def _pass_through_stream(body_iter: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    async for chunk in body_iter:
        yield chunk


async def _observe_safe_visible_output_stream(
    body_iter: AsyncIterator[bytes],
    *,
    dry_run_only: bool,
    max_segment_chars: int,
    min_segment_chars: int,
    pipeline_context: "PipelineContext | None",
) -> AsyncIterator[bytes]:
    frame_buffer = b""
    visible_chunks: list[str] = []
    invalid_observation = False
    try:
        async for chunk in body_iter:
            yield chunk
            if not isinstance(chunk, bytes):
                invalid_observation = True
                continue
            frame_buffer += chunk
            frames, frame_buffer = _split_sse_frames(frame_buffer)
            for frame in frames:
                extracted = _extract_visible_content(frame)
                if extracted is None:
                    continue
                if extracted is False:
                    invalid_observation = True
                    continue
                visible_chunks.append(extracted)
    finally:
        if frame_buffer:
            extracted = _extract_visible_content(frame_buffer)
            if extracted is False:
                invalid_observation = True
            elif isinstance(extracted, str):
                visible_chunks.append(extracted)
        _record_tts_adapter_handoff_results(
            pipeline_context,
            visible_chunks=visible_chunks,
            invalid_observation=invalid_observation,
            dry_run_only=dry_run_only,
            max_segment_chars=max_segment_chars,
            min_segment_chars=min_segment_chars,
        )


def _record_tts_adapter_handoff_results(
    pipeline_context: "PipelineContext | None",
    *,
    visible_chunks: list[str],
    invalid_observation: bool,
    dry_run_only: bool,
    max_segment_chars: int,
    min_segment_chars: int,
) -> None:
    if pipeline_context is None:
        return
    hint_input: tuple[object, ...]
    if invalid_observation:
        hint_input = (object(),)
    else:
        hint_input = tuple(visible_chunks)
    hint_result = build_tts_safe_segmentation_hints(
        hint_input,
        enabled=True,
        dry_run_only=dry_run_only,
        max_segment_chars=max_segment_chars,
        min_segment_chars=min_segment_chars,
    )
    pipeline_context.record_node_result(
        build_relayctx_tts_segmentation_node_result(hint_result)
    )
    handoff_plan = build_tts_adapter_handoff_plan(
        hint_result,
        enabled=True,
        dry_run_only=dry_run_only,
    )
    pipeline_context.record_node_result(
        build_relayctx_tts_adapter_handoff_node_result(handoff_plan)
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


def _extract_visible_content(frame: bytes) -> str | bool | None:
    try:
        text = frame.decode("utf-8")
    except UnicodeDecodeError:
        return False
    payload = _extract_sse_data_payload(text)
    if payload is None or payload == "[DONE]":
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return False
    content_fields = _extract_content_fields(data)
    if not content_fields:
        return None
    if len(content_fields) != 1:
        return False
    return content_fields[0]


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


def _extract_content_fields(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return []
    choices = data.get("choices")
    if not isinstance(choices, list):
        return []
    fields: list[str] = []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        delta = choice.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            fields.append(delta["content"])
        if isinstance(choice.get("text"), str):
            fields.append(choice["text"])
    return fields
