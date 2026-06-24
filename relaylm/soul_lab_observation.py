"""Runtime capture seams for the read-only SOUL Lab observation model.

Capture is deliberately best-effort. Receipt failures never alter the visible
response, RelayCTX injection, Primary MEM persistence, or B3 transitions.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from .relaymem_primary_recall import resolve_relaymem_character_store_root
from .soul_lab_observation_store import (
    OUTCOME_RECEIPT_SCHEMA,
    RUN_RECEIPT_SCHEMA,
    USED_RECEIPT_SCHEMA,
    bounded_text,
    normalize_reason_ids,
    stable_correlation,
    utc_now,
    write_outcome_receipt,
    write_run_receipt,
    write_used_receipt,
)

_PENDING_LIMIT = 1024
_PENDING: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_PENDING_LOCK = threading.RLock()


def capture_primary_worker_observation(request: object, result: object) -> None:
    """Persist one terminal/held/blocked worker outcome without changing it."""

    try:
        status = getattr(result, "status", None)
        outcome_status = {
            "terminal_succeeded": "formed",
            "pipeline_held": "held",
            "terminal_failed": "blocked",
            "pipeline_blocked": "blocked",
            "source_invalid": "blocked",
            "invalid_input": "blocked",
        }.get(status)
        if outcome_status is None:
            return
        store_root = getattr(request, "store_root", None)
        source = getattr(request, "worker_source", None)
        if not isinstance(store_root, str) or source is None:
            return
        run_id = getattr(source, "run_id", None)
        namespace = getattr(source, "namespace", None)
        turn_index = getattr(source, "turn_index", None)
        job_id = getattr(source, "job_id", None)
        if not all(isinstance(value, str) and value for value in (run_id, namespace, job_id)):
            return
        if type(turn_index) is not int or turn_index < 0:
            return
        experience = getattr(source, "governed_experience_artifact", None)
        experience = experience if isinstance(experience, Mapping) else {}
        pipeline = getattr(result, "pipeline_result", None)
        pipeline_status = getattr(pipeline, "status", None)
        reason_ids = normalize_reason_ids(
            (
                *tuple(getattr(result, "reason_ids", ()) or ()),
                *tuple(getattr(pipeline, "reason_ids", ()) or ()),
            )
        )
        payload = {
            "schema": OUTCOME_RECEIPT_SCHEMA,
            "runtime_private": True,
            "read_model_only": True,
            "run_id": run_id,
            "job_correlation_id": stable_correlation(job_id),
            "namespace": namespace,
            "turn_index": turn_index,
            "outcome_status": outcome_status,
            "worker_status": str(status),
            "pipeline_status": str(pipeline_status) if pipeline_status is not None else None,
            "title": bounded_text(experience.get("title"), maximum=160),
            "bounded_summary": bounded_text(
                experience.get("summary_text"), maximum=512
            ),
            "observed_at": utc_now(),
            "reason_ids": reason_ids,
        }
        write_outcome_receipt(store_root, payload)
    except Exception:
        return


def capture_runtime_injection_observation(
    *,
    config: object,
    pipeline_context: object,
    relaymem_retrieval_artifact: object,
    result: object,
) -> None:
    """Capture actual RelayCTX/backend-bound memory evidence best-effort."""

    try:
        _capture_runtime_injection_observation(
            config=config,
            pipeline_context=pipeline_context,
            retrieval=relaymem_retrieval_artifact,
            result=result,
        )
    except Exception:
        return


def _capture_runtime_injection_observation(
    *,
    config: object,
    pipeline_context: object,
    retrieval: object,
    result: object,
) -> None:
    if not isinstance(result, tuple) or len(result) != 3:
        return
    if config is None or pipeline_context is None or not isinstance(retrieval, Mapping):
        return
    route = getattr(pipeline_context, "route", None)
    character_id = getattr(route, "character_id", None)
    namespace = getattr(route, "memory_namespace", None)
    request_id = getattr(pipeline_context, "request_id", None)
    run_id = getattr(pipeline_context, "run_id", None)
    if not all(
        isinstance(value, str) and value
        for value in (character_id, namespace, request_id, run_id)
    ):
        return
    memory = getattr(config, "memory", None)
    configured_root = getattr(memory, "root_path", None)
    if not isinstance(configured_root, str) or not configured_root:
        return
    character_partition = Path(configured_root) / "characters"
    if not (character_partition.exists() or character_partition.is_symlink()):
        return
    scoped_root = resolve_relaymem_character_store_root(configured_root, character_id)
    if not isinstance(scoped_root, str) or not Path(scoped_root).is_dir():
        return

    runtime = retrieval.get("primary_recall_runtime")
    projection = retrieval.get("primary_recall_projection")
    runtime = runtime if isinstance(runtime, Mapping) else {}
    projection = projection if isinstance(projection, Mapping) else {}
    selected = runtime.get("selected_memories")
    selected = selected if isinstance(selected, list) else []
    ctx_result = result[1] if isinstance(result[1], Mapping) else {}
    snippet_result = result[2] if isinstance(result[2], Mapping) else {}
    injection_performed = (
        ctx_result.get("applied") is True or snippet_result.get("applied") is True
    )
    used_items: list[dict[str, str]] = []
    if injection_performed:
        for item in selected[:16]:
            if not isinstance(item, Mapping):
                continue
            memory_id = item.get("idempotency_key")
            if not isinstance(memory_id, str) or len(memory_id) != 64:
                continue
            source_kind = item.get("memory_kind")
            if not isinstance(source_kind, str) or not source_kind:
                source_kind = "primary"
            summary = item.get("snippet_text", item.get("summary"))
            used_items.append(
                {
                    "memory_id": memory_id,
                    "injected_summary": bounded_text(summary, maximum=512),
                    "source_kind": source_kind,
                }
            )
    reasons = normalize_reason_ids(projection.get("blocked_reason_ids", ()))
    used_payload = {
        "schema": USED_RECEIPT_SCHEMA,
        "runtime_private": True,
        "read_model_only": True,
        "request_id": request_id,
        "run_id": run_id,
        "character_id": character_id,
        "namespace": namespace,
        "retrieval_attempted": projection.get("retrieval_attempted") is True,
        "candidate_discovered": bool(selected),
        "selected": bool(selected),
        "relayctx_injection_performed": injection_performed,
        "backend_bound_included": injection_performed,
        "items": used_items,
        "captured_at": utc_now(),
        "reason_ids": reasons,
    }
    write_used_receipt(scoped_root, used_payload)
    repack_status = "applied" if injection_performed else "not_applied"
    pending = {
        "store_root": scoped_root,
        "request_id": request_id,
        "run_id": run_id,
        "character_id": character_id,
        "namespace": namespace,
        "response_mode": "stream"
        if getattr(pipeline_context, "stream_enabled", False)
        else "non_stream",
        "relayctx_repack_status": repack_status,
        "slp_status": "deferred"
        if getattr(config, "relaymem_slp_runtime_enqueue_enabled", False)
        else "disabled",
        "reason_ids": reasons,
    }
    with _PENDING_LOCK:
        _PENDING[request_id] = pending
        _PENDING.move_to_end(request_id)
        while len(_PENDING) > _PENDING_LIMIT:
            _PENDING.popitem(last=False)


def finalize_runtime_observation(
    *,
    request_id: str | None,
    run_id: str | None,
    started_at: str,
    completed_at: str,
    duration_ms: int,
    http_status: int,
) -> None:
    """Finalize a run receipt after the ASGI response body has completed."""

    if not isinstance(request_id, str) or not request_id:
        return
    with _PENDING_LOCK:
        pending = _PENDING.pop(request_id, None)
    if not isinstance(pending, dict):
        return
    if run_id != pending.get("run_id"):
        return
    try:
        payload = {
            "schema": RUN_RECEIPT_SCHEMA,
            "runtime_private": True,
            "read_model_only": True,
            "request_id": request_id,
            "run_id": str(run_id),
            "character_id": pending["character_id"],
            "namespace": pending["namespace"],
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": max(0, min(int(duration_ms), 86_400_000)),
            "response_mode": pending["response_mode"],
            "http_status": int(http_status),
            "relayrun_status": "completed" if http_status < 500 else "failed",
            "relayctx_repack_status": pending["relayctx_repack_status"],
            "relayctx_unpack_status": "not_observed",
            "slp_status": pending["slp_status"],
            "recovery_required": False,
            "reason_ids": pending["reason_ids"],
        }
        write_run_receipt(pending["store_root"], payload)
    except Exception:
        return


class LabObservationResponseMiddleware:
    """Finalize observation only after the actual ASGI response body completes."""

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("path") != "/v1/chat/completions":
            await self.app(scope, receive, send)
            return
        started_wall = datetime.now(timezone.utc).isoformat()
        started_monotonic = time.monotonic()
        response_status = 500
        response_headers: dict[str, str] = {}
        finalized = False

        async def observed_send(message: dict[str, Any]) -> None:
            nonlocal response_status, response_headers, finalized
            if message.get("type") == "http.response.start":
                response_status = int(message.get("status", 500))
                for raw_name, raw_value in message.get("headers", []):
                    try:
                        name = raw_name.decode("latin-1").lower()
                        value = raw_value.decode("latin-1")
                    except (AttributeError, UnicodeError):
                        continue
                    response_headers[name] = value
            await send(message)
            if (
                message.get("type") == "http.response.body"
                and message.get("more_body", False) is False
                and not finalized
            ):
                finalized = True
                completed = datetime.now(timezone.utc).isoformat()
                duration = int(max(0.0, time.monotonic() - started_monotonic) * 1000)
                finalize_runtime_observation(
                    request_id=response_headers.get("x-relaylm-request-id"),
                    run_id=response_headers.get("x-relaylm-run-id"),
                    started_at=started_wall,
                    completed_at=completed,
                    duration_ms=duration,
                    http_status=response_status,
                )

        await self.app(scope, receive, observed_send)


__all__ = [
    "LabObservationResponseMiddleware",
    "capture_primary_worker_observation",
    "capture_runtime_injection_observation",
    "finalize_runtime_observation",
]
