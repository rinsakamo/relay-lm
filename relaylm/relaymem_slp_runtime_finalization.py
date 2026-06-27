"""Post-response Phase 6 I1-B runtime finalization.

The stream observer is byte-preserving and sits outside RelayCTX suppression and
TTS handoff. The background function runs only after response delivery, persists
protected source before queue publication, and records only content-free nodes.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.diagnostics import RequestDiagnostics
from relaylm.pipeline_context import PipelineContext
from relaylm.relaymem_slp_durable_finalization_publication import (
    RelayMEMSLPDurableFinalizationError,
    RelayMEMSLPDurableFinalizationPreparedTurn,
    RelayMEMSLPDurableFinalizationPreparedTurnHolder,
    RelayMEMSLPDurableFinalizationStreamSession,
)
from relaylm.relaymem_slp_durable_finalization_record import derive_locator_digest
from relaylm.relaymem_slp_durable_finalization_replay import (
    build_relaymem_slp_durable_finalization_replay_node_result,
    replay_relaymem_slp_durable_finalization_record,
)
from relaylm.relaymem_slp_durable_runtime_enqueue import (
    RelayMEMSLPDurableRuntimeEnqueueResult,
    apply_relaymem_slp_durable_runtime_enqueue,
    build_relaymem_slp_durable_runtime_enqueue_failure_result,
    build_relaymem_slp_durable_runtime_enqueue_node_result,
)
from relaylm.relaymem_slp_finalized_turn_source import (
    RelayMEMSLPFinalizedTurnSourceResult,
    build_relaymem_slp_finalized_turn_source,
    build_relaymem_slp_finalized_turn_source_node_result,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_protected_source_store import (
    RelayMEMSLPDurableProtectedSourceStore,
)
from relaylm.relaymem_slp_runtime_enqueue import (
    build_relaymem_slp_runtime_enqueue_failure_result,
)
from relaylm.trace_runtime import trace_runtime_event
from relaylm.trusted_home_scene_admission import (
    build_trusted_home_scene_admission_node_result,
    resolve_trusted_home_scene_admission,
    trusted_home_scene_runtime_gate,
)

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
    durable_session: RelayMEMSLPDurableFinalizationStreamSession | None = None,
) -> AsyncIterator[bytes]:
    """Observe SSE, using pre-yield durable admission only for I1-GB apply."""

    if type(capture) is not RelayMEMSLPFinalizedVisibleTextCapture:
        raise TypeError("exact_stream_capture_required")
    if durable_session is not None and type(
        durable_session
    ) is not RelayMEMSLPDurableFinalizationStreamSession:
        raise TypeError("exact_durable_finalization_stream_session_required")
    return (
        _observe_before_yield(body_iter, capture, durable_session)
        if durable_session is not None
        else _observe_after_yield(body_iter, capture)
    )


async def _observe_after_yield(
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


async def _observe_before_yield(
    body_iter: AsyncIterator[bytes],
    capture: RelayMEMSLPFinalizedVisibleTextCapture,
    durable_session: RelayMEMSLPDurableFinalizationStreamSession,
) -> AsyncIterator[bytes]:
    frame_buffer = b""
    normal_completion = False
    try:
        async for chunk in body_iter:
            if type(chunk) is not bytes:
                raise RelayMEMSLPDurableFinalizationError(
                    "durable_finalization_stream_chunk_type_invalid"
                )
            frame_buffer += chunk
            frames, frame_buffer = _split_sse_frames(frame_buffer)
            for frame in frames:
                await _admit_frame_before_yield(frame, capture, durable_session)
                yield frame
        if frame_buffer:
            await _admit_frame_before_yield(
                frame_buffer, capture, durable_session
            )
            yield frame_buffer
            frame_buffer = b""
        if not durable_session.sealed:
            durable_session.seal()
        capture.finalize()
        normal_completion = True
    except asyncio.CancelledError:
        capture.invalidate()
        durable_session.abort()
        raise
    except RelayMEMSLPDurableFinalizationError:
        capture.invalidate()
        durable_session.abort()
        raise
    except Exception:
        capture.invalidate()
        durable_session.abort()
        raise RelayMEMSLPDurableFinalizationError(
            "durable_finalization_stream_backend_failed"
        ) from None
    finally:
        if not normal_completion:
            capture.invalidate()
            durable_session.abort()


async def _admit_frame_before_yield(
    frame: bytes,
    capture: RelayMEMSLPFinalizedVisibleTextCapture,
    durable_session: RelayMEMSLPDurableFinalizationStreamSession,
) -> None:
    payload = _strict_sse_payload(frame)
    if payload is None:
        return
    if payload == "[DONE]":
        durable_session.seal()
        capture.finalize()
        return
    data = _strict_json_object(payload)
    fields = _extract_content_fields(data)
    if len(fields) > 1:
        raise RelayMEMSLPDurableFinalizationError(
            "durable_finalization_stream_content_ambiguous"
        )
    if fields and fields[0]:
        durable_session.publish_content_unit(fields[0])
        capture.append(fields[0])


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
    prepared_turn: RelayMEMSLPDurableFinalizationPreparedTurn | None = None,
    prepared_turn_holder: RelayMEMSLPDurableFinalizationPreparedTurnHolder | None = None,
    message_count: int = 0,
) -> RelayMEMSLPDurableRuntimeEnqueueResult:
    """Converge source, queue, and I1-G completion after response delivery."""

    source_result: RelayMEMSLPFinalizedTurnSourceResult | None = None
    replay_node = None
    admission_node = None
    enqueue_enabled = config.relaymem_slp_runtime_enqueue_enabled
    enqueue_dry_run_only = config.relaymem_slp_runtime_enqueue_dry_run_only
    enqueue_apply_enabled = config.relaymem_slp_runtime_enqueue_apply_enabled
    try:
        admission_decision = resolve_trusted_home_scene_admission(
            config=config,
            route=pipeline_context.route,
            payload=pipeline_context.original_payload,
        )
        admission_node = build_trusted_home_scene_admission_node_result(
            admission_decision
        )
        (
            enqueue_enabled,
            enqueue_dry_run_only,
            enqueue_apply_enabled,
        ) = trusted_home_scene_runtime_gate(config, admission_decision)

        exact_prepared = prepared_turn
        if prepared_turn_holder is not None:
            if type(prepared_turn_holder) is not RelayMEMSLPDurableFinalizationPreparedTurnHolder:
                raise TypeError("exact_durable_finalization_holder_required")
            exact_prepared = prepared_turn_holder.get()
        if exact_prepared is not None and type(
            exact_prepared
        ) is not RelayMEMSLPDurableFinalizationPreparedTurn:
            raise TypeError("exact_durable_finalization_prepared_turn_required")

        durable_replay_enabled = bool(
            exact_prepared is not None
            and config.relaymem_slp_durable_finalization_enabled
            and config.relaymem_slp_durable_finalization_apply_enabled
            and not config.relaymem_slp_durable_finalization_dry_run_only
        )
        if durable_replay_enabled:
            assert exact_prepared is not None
            source_result = exact_prepared.source_result
            source = source_result.source
            if source is None:
                raise RelayMEMSLPDurableFinalizationError(
                    "durable_finalization_sealed_source_required"
                )
            locator = derive_locator_digest(
                run_id=source.run_id,
                turn_index=source.turn_index,
                character_id=source.character_id,
            )
            replay = replay_relaymem_slp_durable_finalization_record(
                config,
                locator_digest=locator,
                registry=registry,
            )
            replay_node = build_relaymem_slp_durable_finalization_replay_node_result(
                replay
            )
            result = replay.durable_runtime_result
            if result is None:
                runtime_failure = build_relaymem_slp_runtime_enqueue_failure_result(
                    "durable_finalization_replay_not_converged"
                )
                result = build_relaymem_slp_durable_runtime_enqueue_failure_result(
                    runtime_failure,
                    "durable_finalization_replay_not_converged",
                )
        else:
            if exact_prepared is not None:
                source_result = exact_prepared.source_result
            else:
                if (
                    config.relaymem_slp_durable_finalization_enabled
                    and config.relaymem_slp_durable_finalization_apply_enabled
                    and not config.relaymem_slp_durable_finalization_dry_run_only
                ):
                    raise RelayMEMSLPDurableFinalizationError(
                        "durable_finalization_sealed_preparation_required"
                    )
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
                    enabled=enqueue_enabled,
                )
            source_store = (
                RelayMEMSLPDurableProtectedSourceStore(
                    config.relaymem_slp_protected_source_root,
                    max_artifact_bytes=(
                        config.relaymem_slp_protected_source_max_artifact_bytes
                    ),
                )
                if config.relaymem_slp_protected_source_root is not None
                else None
            )
            result = apply_relaymem_slp_durable_runtime_enqueue(
                source_result,
                registry=registry,
                source_store=source_store,
                queue_root=config.relaymem_slp_queue_root,
                enabled=enqueue_enabled,
                dry_run_only=enqueue_dry_run_only,
                apply_enabled=enqueue_apply_enabled,
                prepared_result=(
                    exact_prepared.runtime_preparation
                    if exact_prepared is not None
                    else None
                ),
            )
    except Exception:
        runtime_failure = build_relaymem_slp_runtime_enqueue_failure_result()
        result = build_relaymem_slp_durable_runtime_enqueue_failure_result(
            runtime_failure
        )

    nodes = []
    try:
        if admission_node is not None:
            nodes.append(admission_node)
        if source_result is not None:
            nodes.append(
                build_relaymem_slp_finalized_turn_source_node_result(source_result)
            )
        if replay_node is not None:
            nodes.append(replay_node)
        nodes.append(build_relaymem_slp_durable_runtime_enqueue_node_result(result))
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
    except Exception:
        pass
    finally:
        runtime_result = result.runtime_result
        if (
            runtime_result.status == "dry_run_ready"
            and runtime_result.source_scope is not None
        ):
            runtime_result.source_scope.close()
    return result


def _strict_sse_payload(frame: bytes) -> str | None:
    try:
        text = frame.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RelayMEMSLPDurableFinalizationError(
            "durable_finalization_stream_malformed_utf8"
        ) from None
    return _extract_sse_data_payload(text)


def _strict_json_object(payload: str) -> object:
    duplicate = False

    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        nonlocal duplicate
        result: dict[str, object] = {}
        for key, value in pairs:
            duplicate = duplicate or key in result
            result[key] = value
        return result

    def reject_nonfinite(_: str) -> object:
        raise ValueError("non-finite JSON")

    try:
        value = json.loads(
            payload,
            object_pairs_hook=object_pairs,
            parse_constant=reject_nonfinite,
        )
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise RelayMEMSLPDurableFinalizationError(
            "durable_finalization_stream_malformed_json"
        ) from None
    if duplicate:
        raise RelayMEMSLPDurableFinalizationError(
            "durable_finalization_stream_duplicate_json_key"
        )
    return value


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
