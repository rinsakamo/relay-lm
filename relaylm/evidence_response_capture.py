"""Public EV-1 assistant-response capture API.

Non-stream apply is supported. Streaming is validation-only until durable
cross-process finalization recovery is implemented; runtime apply fails closed
before the backend stream is exposed.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone

from relaylm.evidence_response_admission import (
    finalize_response_capture,
    terminalize_no_output,
)
from relaylm.evidence_response_result import EvidenceResponseCaptureResult
from relaylm.evidence_response_session import (
    MAX_ASSISTANT_TEXT_CHARS,
    WORKSPACE_REF,
    PreparedResponseCapture,
    derive_id,
    prepare_response_capture,
)
from relaylm.evidence_space import derive_evidence_space_id
from relaylm.evidence_store import EvidenceRecordStore

_SSE_SEPARATORS = (b"\r\n\r\n", b"\n\n")
_MAX_PENDING_SSE_FRAME_BYTES = MAX_ASSISTANT_TEXT_CHARS * 4 + 65_536


@dataclass(frozen=True)
class _FrameObservation:
    texts: tuple[str, ...] = ()
    done: bool = False
    finish_reason: str | None = None
    blocked_reason: str | None = None


def capture_managed_assistant_response_nonstream(
    *,
    store: EvidenceRecordStore | None,
    apply_enabled: bool,
    character_id: str | None,
    memory_namespace: str | None,
    session_id: str | None,
    response_id: str,
    delivery_cohort_id: str,
    request_source_event_ids: tuple[str, ...],
    assistant_visible_text: str | None,
    completion_extent: str = "response_complete",
    termination_cause: str = "normal",
    operation_idempotency_key: str,
    route_snapshot_payload: dict[str, object] | None = None,
    now: datetime | None = None,
) -> EvidenceResponseCaptureResult:
    existing = _existing_nonstream_result(
        store=store,
        apply_enabled=apply_enabled,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        assistant_visible_text=assistant_visible_text,
        operation_idempotency_key=operation_idempotency_key,
    )
    if existing is not None:
        return existing
    prepared, reasons = prepare_response_capture(
        store=store,
        apply_enabled=apply_enabled,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        response_id=response_id,
        delivery_cohort_id=delivery_cohort_id,
        request_source_event_ids=request_source_event_ids,
        operation_idempotency_key=operation_idempotency_key,
        route_snapshot_payload=route_snapshot_payload,
        now=now,
    )
    if prepared is None:
        return EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=reasons
        )
    observed_at = (now or datetime.now(timezone.utc)).isoformat()
    restored_text = "".join(prepared.accepted_parts)
    if not isinstance(assistant_visible_text, str) or not assistant_visible_text:
        if restored_text:
            return EvidenceResponseCaptureResult(
                status="integrity_conflict",
                blocked_reasons=("assistant_response_recovery_output_conflict",),
                evidence_space_id=prepared.descriptor.evidence_space_id,
                persisted=prepared.apply_enabled,
            )
        return terminalize_no_output(prepared, terminal_at=observed_at)
    if not assistant_visible_text.startswith(restored_text):
        return EvidenceResponseCaptureResult(
            status="integrity_conflict",
            blocked_reasons=("assistant_response_recovery_output_conflict",),
            evidence_space_id=prepared.descriptor.evidence_space_id,
            persisted=prepared.apply_enabled,
        )
    missing_text = assistant_visible_text[len(restored_text) :]
    if missing_text:
        ok, observe_reasons = prepared.observe(missing_text, observed_at)
        if not ok:
            return EvidenceResponseCaptureResult(
                status="fail_closed",
                blocked_reasons=observe_reasons,
                evidence_space_id=prepared.descriptor.evidence_space_id,
                persisted=prepared.apply_enabled,
            )
    return finalize_response_capture(
        prepared,
        completion_extent=completion_extent,
        termination_cause=termination_cause,
        finalized_at=observed_at,
    )


def prepare_stream_with_evidence_response_capture(
    body_iter: AsyncIterator[bytes],
    *,
    store: EvidenceRecordStore | None,
    apply_enabled: bool,
    character_id: str | None,
    memory_namespace: str | None,
    session_id: str | None,
    response_id: str,
    delivery_cohort_id: str,
    request_source_event_ids: tuple[str, ...],
    operation_idempotency_key: str,
    route_snapshot_payload: dict[str, object] | None = None,
    on_finalized=None,
) -> tuple[AsyncIterator[bytes] | None, EvidenceResponseCaptureResult | None]:
    if apply_enabled:
        return None, EvidenceResponseCaptureResult(
            status="fail_closed",
            blocked_reasons=("evidence_stream_apply_requires_recovery_support",),
        )
    prepared, reasons = prepare_response_capture(
        store=store,
        apply_enabled=False,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        response_id=response_id,
        delivery_cohort_id=delivery_cohort_id,
        request_source_event_ids=request_source_event_ids,
        operation_idempotency_key=operation_idempotency_key,
        route_snapshot_payload=route_snapshot_payload,
    )
    if prepared is None:
        return body_iter, EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=reasons
        )
    return _observe_prepared_stream(body_iter, prepared=prepared, on_finalized=on_finalized), None


def wrap_stream_with_evidence_response_capture(
    body_iter: AsyncIterator[bytes],
    *,
    store: EvidenceRecordStore | None,
    apply_enabled: bool,
    character_id: str | None,
    memory_namespace: str | None,
    session_id: str | None,
    response_id: str,
    delivery_cohort_id: str,
    request_source_event_ids: tuple[str, ...],
    operation_idempotency_key: str,
    route_snapshot_payload: dict[str, object] | None = None,
    on_finalized=None,
) -> AsyncIterator[bytes]:
    wrapped, preflight = prepare_stream_with_evidence_response_capture(
        body_iter,
        store=store,
        apply_enabled=apply_enabled,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
        response_id=response_id,
        delivery_cohort_id=delivery_cohort_id,
        request_source_event_ids=request_source_event_ids,
        operation_idempotency_key=operation_idempotency_key,
        route_snapshot_payload=route_snapshot_payload,
        on_finalized=on_finalized,
    )
    if preflight is not None:
        _notify(on_finalized, preflight)
    return wrapped if wrapped is not None else _stop_stream(body_iter)


async def _stop_stream(body_iter: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    aclose = getattr(body_iter, "aclose", None)
    if callable(aclose):
        try:
            await aclose()
        except Exception:
            pass
    if False:
        yield b""


async def _observe_prepared_stream(
    body_iter: AsyncIterator[bytes],
    *,
    prepared: PreparedResponseCapture,
    on_finalized,
) -> AsyncIterator[bytes]:
    completion_extent = "response_complete"
    termination_cause = "normal"
    frame_buffer = b""
    observation_disabled = False
    saw_done = False
    finish_reason: str | None = None
    try:
        async for chunk in body_iter:
            blocked: str | None = None
            if isinstance(chunk, bytes) and not observation_disabled:
                if len(frame_buffer) + len(chunk) > _MAX_PENDING_SSE_FRAME_BYTES:
                    blocked = "assistant_stream_frame_buffer_limit_exceeded"
                    frame_buffer = b""
                    observation_disabled = True
                else:
                    frame_buffer += chunk
                    frames, frame_buffer = _split_sse_frames(frame_buffer)
                    for frame in frames:
                        observation = _inspect_frame(frame)
                        if observation.blocked_reason is not None:
                            blocked = observation.blocked_reason
                            break
                        saw_done = saw_done or observation.done
                        if observation.finish_reason is not None:
                            finish_reason = observation.finish_reason
                        for text in observation.texts:
                            ok, observe_reasons = prepared.observe(
                                text, datetime.now(timezone.utc).isoformat()
                            )
                            if not ok:
                                blocked = (
                                    observe_reasons[0]
                                    if observe_reasons
                                    else "assistant_output_observation_failed"
                                )
                                break
                        if blocked is not None:
                            break
            if blocked is not None:
                prepared.invalid_reason = blocked
            # Dry-run is diagnostic-only: never alter the existing stream.
            yield chunk
        if frame_buffer:
            observation = _inspect_frame(frame_buffer)
            if observation.blocked_reason is not None:
                prepared.invalid_reason = observation.blocked_reason
            else:
                saw_done = saw_done or observation.done
                if observation.finish_reason is not None:
                    finish_reason = observation.finish_reason
                for text in observation.texts:
                    ok, reasons = prepared.observe(
                        text, datetime.now(timezone.utc).isoformat()
                    )
                    if not ok:
                        prepared.invalid_reason = (
                            reasons[0]
                            if reasons
                            else "assistant_output_observation_failed"
                        )
                        break
        if not saw_done:
            completion_extent = "response_partial"
            termination_cause = "transport_error"
        elif finish_reason == "length":
            termination_cause = "model_limit"
        elif finish_reason == "content_filter":
            termination_cause = "safety_stop"
        elif finish_reason not in {None, "stop"}:
            prepared.invalid_reason = "assistant_stream_finish_reason_unsupported"
    except asyncio.CancelledError:
        completion_extent = "response_partial"
        termination_cause = "user_cancel"
        raise
    except GeneratorExit:
        completion_extent = "response_partial"
        termination_cause = "runtime_cancel"
        raise
    except BaseException:
        completion_extent = "response_partial"
        termination_cause = "backend_error"
        raise
    finally:
        result = finalize_response_capture(
            prepared,
            completion_extent=completion_extent,
            termination_cause=termination_cause,
        )
        _notify(on_finalized, result)


def _notify(callback, result: EvidenceResponseCaptureResult) -> None:
    if callback is None:
        return
    try:
        callback(result)
    except Exception:
        pass


def _existing_nonstream_result(
    *,
    store: EvidenceRecordStore | None,
    apply_enabled: bool,
    character_id: str | None,
    memory_namespace: str | None,
    session_id: str | None,
    assistant_visible_text: str | None,
    operation_idempotency_key: str,
) -> EvidenceResponseCaptureResult | None:
    if (
        not apply_enabled
        or store is None
        or not isinstance(character_id, str)
        or not isinstance(memory_namespace, str)
        or not isinstance(session_id, str)
    ):
        return None
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref=WORKSPACE_REF,
        character_id=character_id,
        memory_namespace=memory_namespace,
        session_id=session_id,
    )
    source_event_id = derive_id(
        "sourceevent", operation_idempotency_key, "source_event"
    )
    source = store.read_record(
        evidence_space_id=evidence_space_id,
        record_kind="source_event",
        record_id=source_event_id,
    )
    if source is None:
        return None
    parts = source.get("canonical_source_manifest", {}).get("parts", [])
    expected_digest = (
        parts[0].get("content_digest_or_null")
        if isinstance(parts, list)
        and len(parts) == 1
        and isinstance(parts[0], dict)
        else None
    )
    actual_digest = (
        hashlib.sha256(assistant_visible_text.encode("utf-8")).hexdigest()
        if isinstance(assistant_visible_text, str) and assistant_visible_text
        else None
    )
    if expected_digest != actual_digest:
        return EvidenceResponseCaptureResult(
            status="integrity_conflict",
            blocked_reasons=("source_event_integrity_conflict",),
            evidence_space_id=evidence_space_id,
            source_event_id=source_event_id,
        )
    return EvidenceResponseCaptureResult(
        status="admitted",
        evidence_space_id=evidence_space_id,
        source_event_id=source_event_id,
        admission_decision_id=derive_id(
            "admdecision", operation_idempotency_key, "admission"
        ),
        persisted=True,
    )


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


def _inspect_frame(frame: bytes) -> _FrameObservation:
    try:
        text = frame.decode("utf-8")
    except UnicodeDecodeError:
        return _FrameObservation(blocked_reason="assistant_stream_utf8_invalid")
    payload = _extract_sse_data_payload(text)
    if payload is None:
        return _FrameObservation()
    if payload == "[DONE]":
        return _FrameObservation(done=True)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return _FrameObservation(blocked_reason="assistant_stream_json_invalid")
    if not isinstance(data, dict):
        return _FrameObservation(blocked_reason="assistant_stream_payload_invalid")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        return _FrameObservation(
            blocked_reason="assistant_stream_requires_exactly_one_choice"
        )
    choice = choices[0]
    if not isinstance(choice, dict) or choice.get("index", 0) != 0:
        return _FrameObservation(blocked_reason="assistant_stream_choice_invalid")
    delta = choice.get("delta")
    texts: list[str] = []
    if isinstance(delta, dict):
        if delta.get("tool_calls") is not None or delta.get("function_call") is not None:
            return _FrameObservation(
                blocked_reason="assistant_stream_tool_call_unsupported"
            )
        content = delta.get("content")
        if content is not None and not isinstance(content, str):
            return _FrameObservation(
                blocked_reason="assistant_stream_content_invalid"
            )
        if isinstance(content, str):
            texts.append(content)
    if isinstance(choice.get("text"), str):
        texts.append(choice["text"])
    finish = choice.get("finish_reason")
    if finish is not None and not isinstance(finish, str):
        return _FrameObservation(
            blocked_reason="assistant_stream_finish_reason_invalid"
        )
    return _FrameObservation(texts=tuple(texts), finish_reason=finish)


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


__all__ = [
    "EvidenceResponseCaptureResult",
    "capture_managed_assistant_response_nonstream",
    "prepare_stream_with_evidence_response_capture",
    "wrap_stream_with_evidence_response_capture",
]
