"""Config-gated managed-chat integration facade for the bounded EV-1 slice."""
from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from relaylm.evidence_response_capture import (
    EvidenceResponseCaptureResult,
    capture_managed_assistant_response_nonstream,
    prepare_stream_with_evidence_response_capture,
)
from relaylm.evidence_space import derive_evidence_space_id
from relaylm.evidence_store import EvidenceRecordStore
from relaylm.evidence_user_input import (
    EvidenceUserInputCaptureResult,
    capture_managed_user_input,
)
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.route_capture_authority import issue_managed_route_capture_snapshot

if TYPE_CHECKING:
    from relaylm.config import RelayLMConfig
    from relaylm.pipeline_context import PipelineContext
    from relaylm.routing import ResolvedRoute

_store_cache: dict[str, EvidenceRecordStore] = {}
_WORKSPACE_REF = "relaylm-local"


@dataclass(frozen=True)
class EvidenceRuntimeGate:
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    blocked_reasons: tuple[str, ...] = ()

    @property
    def active(self) -> bool:
        return self.enabled

    @property
    def applies(self) -> bool:
        return self.enabled and self.apply_enabled and not self.dry_run_only


def _private_session_ref(route: "ResolvedRoute") -> str | None:
    if not isinstance(route.user_id, str) or not route.user_id:
        return None
    if not isinstance(route.session_id, str) or not route.session_id:
        return None
    digest = hashlib.sha256(
        f"{route.user_id}\0{route.session_id}".encode("utf-8")
    ).hexdigest()
    return f"privateconversation_{digest}"


def resolve_evidence_gate(
    config: "RelayLMConfig",
    route: "ResolvedRoute",
    resolved_scope: Mapping[str, object] | None = None,
    *,
    stream_enabled: bool = False,
) -> EvidenceRuntimeGate:
    if route.mode_applied == "pass_through" or not config.evidence_capture_enabled:
        return EvidenceRuntimeGate(False, True, False)
    reasons: list[str] = []
    if not isinstance(route.user_id, str) or not route.user_id:
        reasons.append("evidence_private_route_user_required")
    if not isinstance(route.session_id, str) or not route.session_id:
        reasons.append("evidence_private_route_session_required")
    if route.room_id is not None or route.scene_id is not None:
        reasons.append("evidence_shared_scope_unsupported_in_ev1")
    if resolved_scope is not None:
        for key in ("user_id", "session_id", "room_id", "scene_id"):
            if resolved_scope.get(key) != getattr(route, key):
                reasons.append(f"evidence_route_scope_conflict:{key}")
    applies = (
        bool(config.evidence_capture_enabled)
        and bool(config.evidence_capture_apply_enabled)
        and not bool(config.evidence_capture_dry_run_only)
    )
    if stream_enabled and applies:
        reasons.append("evidence_stream_apply_requires_recovery_support")
    return EvidenceRuntimeGate(
        enabled=True,
        dry_run_only=bool(config.evidence_capture_dry_run_only),
        apply_enabled=bool(config.evidence_capture_apply_enabled),
        blocked_reasons=tuple(dict.fromkeys(reasons)),
    )


def _evidence_store_for_gate(
    config: "RelayLMConfig", gate: EvidenceRuntimeGate
) -> tuple[EvidenceRecordStore | None, tuple[str, ...]]:
    """Construct storage only for apply; dry-run must not touch the filesystem."""

    if not gate.applies:
        return None, ()
    root = config.evidence_data_root
    if root is None:
        return None, ("evidence_store_root_missing",)
    cached = _store_cache.get(root)
    if cached is not None:
        return cached, ()
    try:
        store = EvidenceRecordStore(root)
    except ValueError as exc:
        return None, (str(exc),)
    _store_cache[root] = store
    return store, ()


def _snapshot_for(
    *,
    pipeline_context: "PipelineContext",
    resolved_scope: Mapping[str, object],
    private_session_ref: str,
    capture_profile: str,
) -> tuple[dict[str, object] | None, tuple[str, ...]]:
    route = pipeline_context.route
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref=_WORKSPACE_REF,
        character_id=route.character_id or "",
        memory_namespace=route.memory_namespace or "",
        session_id=private_session_ref,
    )
    return issue_managed_route_capture_snapshot(
        route=route,
        resolved_scope=resolved_scope,
        evidence_space_id=evidence_space_id,
        capture_profile=capture_profile,
    )


def capture_evidence_for_user_input(
    *,
    config: "RelayLMConfig",
    pipeline_context: "PipelineContext",
    resolved_scope: Mapping[str, object],
) -> PipelineNodeResult | None:
    gate = resolve_evidence_gate(
        config,
        pipeline_context.route,
        resolved_scope,
        stream_enabled=False,
    )
    if not gate.enabled:
        return None
    fail_closed_reasons: list[str] = list(gate.blocked_reasons)
    store, store_reasons = _evidence_store_for_gate(config, gate)
    fail_closed_reasons.extend(store_reasons)

    current_user_text: str | None = None
    preflight = pipeline_context.client_history_exclusion_preflight_result
    if preflight is None:
        fail_closed_reasons.append("evidence_current_user_preflight_unavailable")
    elif preflight.status not in {"ready", "pending"}:
        fail_closed_reasons.extend(
            tuple(preflight.blocked_reasons)
            or ("evidence_current_user_preflight_not_ready",)
        )
    else:
        message = preflight.current_user_message
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content:
            current_user_text = content
        elif (
            isinstance(content, list)
            and len(content) == 1
            and isinstance(content[0], dict)
            and content[0].get("type") in ("text", "input_text")
            and isinstance(content[0].get("text"), str)
            and content[0].get("text")
        ):
            current_user_text = content[0]["text"]
        else:
            fail_closed_reasons.append(
                "evidence_current_user_content_not_single_text_occurrence"
            )

    private_session_ref = _private_session_ref(pipeline_context.route)
    snapshot: dict[str, object] | None = None
    if private_session_ref is None:
        fail_closed_reasons.append("evidence_private_conversation_identity_unavailable")
    else:
        snapshot, snapshot_reasons = _snapshot_for(
            pipeline_context=pipeline_context,
            resolved_scope=resolved_scope,
            private_session_ref=private_session_ref,
            capture_profile="managed_user_input",
        )
        fail_closed_reasons.extend(snapshot_reasons)

    result = capture_managed_user_input(
        store=store,
        apply_enabled=gate.applies,
        character_id=pipeline_context.route.character_id,
        memory_namespace=pipeline_context.route.memory_namespace,
        session_id=private_session_ref,
        current_user_text=current_user_text,
        fail_closed_reasons=tuple(dict.fromkeys(fail_closed_reasons)),
        operation_idempotency_key=f"{pipeline_context.request_id}:user_input",
        route_snapshot_payload=snapshot,
    )
    pipeline_context.set_evidence_user_input_capture_result(result)
    return _node_result("evidence_user_input_capture", result)


def _classify_nonstream_response(
    body: object,
) -> tuple[str | None, str, str, tuple[str, ...]]:
    reasons: list[str] = []
    if not isinstance(body, dict):
        return None, "response_partial", "unknown", (
            "evidence_response_body_invalid",
        )
    choices = body.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        return None, "response_partial", "unknown", (
            "evidence_response_requires_exactly_one_choice",
        )
    choice = choices[0]
    if not isinstance(choice, dict) or choice.get("index", 0) != 0:
        return None, "response_partial", "unknown", (
            "evidence_response_choice_invalid",
        )
    text: str | None = None
    message = choice.get("message")
    if isinstance(message, dict):
        if message.get("tool_calls") is not None or message.get("function_call") is not None:
            reasons.append("evidence_response_tool_call_unsupported")
        content = message.get("content")
        if isinstance(content, str):
            text = content
        else:
            reasons.append("evidence_response_requires_text_content")
    elif isinstance(choice.get("text"), str):
        text = choice["text"]
    else:
        reasons.append("evidence_response_requires_text_content")

    finish_reason = choice.get("finish_reason")
    axes = {
        None: ("response_complete", "normal"),
        "stop": ("response_complete", "normal"),
        "length": ("response_complete", "model_limit"),
        "content_filter": ("response_complete", "safety_stop"),
    }.get(finish_reason)
    if axes is None:
        reasons.append("evidence_response_finish_reason_unsupported")
        axes = ("response_partial", "unknown")
    return text, axes[0], axes[1], tuple(dict.fromkeys(reasons))


def capture_evidence_for_assistant_response_nonstream(
    *,
    config: "RelayLMConfig",
    pipeline_context: "PipelineContext",
    resolved_scope: Mapping[str, object],
    response_id: str,
    response_body: object,
) -> PipelineNodeResult | None:
    gate = resolve_evidence_gate(config, pipeline_context.route, resolved_scope)
    if not gate.enabled:
        return None
    store, store_reasons = _evidence_store_for_gate(config, gate)
    text, completion_extent, termination_cause, shape_reasons = (
        _classify_nonstream_response(response_body)
    )
    reasons = [*gate.blocked_reasons, *store_reasons, *shape_reasons]
    private_session_ref = _private_session_ref(pipeline_context.route)
    snapshot: dict[str, object] | None = None
    if private_session_ref is None:
        reasons.append("evidence_private_conversation_identity_unavailable")
    else:
        snapshot, snapshot_reasons = _snapshot_for(
            pipeline_context=pipeline_context,
            resolved_scope=resolved_scope,
            private_session_ref=private_session_ref,
            capture_profile="managed_assistant_response",
        )
        reasons.extend(snapshot_reasons)
    if reasons:
        return _node_result(
            "evidence_assistant_response_capture",
            EvidenceResponseCaptureResult(
                status="fail_closed", blocked_reasons=tuple(dict.fromkeys(reasons))
            ),
        )

    user_capture = pipeline_context.evidence_user_input_capture_result
    request_source_event_ids = (
        (user_capture.source_event_id,)
        if user_capture is not None and user_capture.source_event_id is not None
        else ()
    )
    result = capture_managed_assistant_response_nonstream(
        store=store,
        apply_enabled=gate.applies,
        character_id=pipeline_context.route.character_id,
        memory_namespace=pipeline_context.route.memory_namespace,
        session_id=private_session_ref,
        response_id=response_id,
        delivery_cohort_id=f"{pipeline_context.request_id}:cohort",
        request_source_event_ids=request_source_event_ids,
        assistant_visible_text=text,
        completion_extent=completion_extent,
        termination_cause=termination_cause,
        operation_idempotency_key=f"{pipeline_context.request_id}:assistant_response",
        route_snapshot_payload=snapshot,
    )
    return _node_result("evidence_assistant_response_capture", result)


def prepare_stream_evidence_response_capture(
    body_iter: AsyncIterator[bytes],
    *,
    config: "RelayLMConfig",
    pipeline_context: "PipelineContext",
    resolved_scope: Mapping[str, object],
    response_id: str,
    on_finalized=None,
) -> tuple[AsyncIterator[bytes] | None, PipelineNodeResult | None]:
    gate = resolve_evidence_gate(
        config,
        pipeline_context.route,
        resolved_scope,
        stream_enabled=True,
    )
    if not gate.enabled:
        return body_iter, None
    if gate.blocked_reasons:
        result = EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=gate.blocked_reasons
        )
        node = _node_result("evidence_assistant_response_capture", result)
        return (None if gate.applies else body_iter), node
    store, store_reasons = _evidence_store_for_gate(config, gate)
    if store_reasons:
        result = EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=store_reasons
        )
        return (None if gate.applies else body_iter), _node_result(
            "evidence_assistant_response_capture", result
        )
    private_session_ref = _private_session_ref(pipeline_context.route)
    if private_session_ref is None:
        result = EvidenceResponseCaptureResult(
            status="fail_closed",
            blocked_reasons=("evidence_private_conversation_identity_unavailable",),
        )
        return (None if gate.applies else body_iter), _node_result(
            "evidence_assistant_response_capture", result
        )
    snapshot, snapshot_reasons = _snapshot_for(
        pipeline_context=pipeline_context,
        resolved_scope=resolved_scope,
        private_session_ref=private_session_ref,
        capture_profile="managed_assistant_response",
    )
    if snapshot_reasons:
        result = EvidenceResponseCaptureResult(
            status="fail_closed", blocked_reasons=snapshot_reasons
        )
        return (None if gate.applies else body_iter), _node_result(
            "evidence_assistant_response_capture", result
        )
    user_capture = pipeline_context.evidence_user_input_capture_result
    request_source_event_ids = (
        (user_capture.source_event_id,)
        if user_capture is not None and user_capture.source_event_id is not None
        else ()
    )
    wrapped, preflight = prepare_stream_with_evidence_response_capture(
        body_iter,
        store=store,
        apply_enabled=gate.applies,
        character_id=pipeline_context.route.character_id,
        memory_namespace=pipeline_context.route.memory_namespace,
        session_id=private_session_ref,
        response_id=response_id,
        delivery_cohort_id=f"{pipeline_context.request_id}:cohort",
        request_source_event_ids=request_source_event_ids,
        operation_idempotency_key=f"{pipeline_context.request_id}:assistant_response",
        route_snapshot_payload=snapshot,
        on_finalized=on_finalized,
    )
    if preflight is not None:
        node = _node_result("evidence_assistant_response_capture", preflight)
        return (None if gate.applies else body_iter), node
    return wrapped, None


def build_evidence_response_capture_node_result(
    result: EvidenceResponseCaptureResult,
) -> PipelineNodeResult:
    return _node_result("evidence_assistant_response_capture", result)


def _node_result(
    node_name: str,
    result: EvidenceUserInputCaptureResult | EvidenceResponseCaptureResult,
) -> PipelineNodeResult:
    status = {
        "admitted": "applied",
        "dry_run_ready": "diagnostic_only",
        "terminal_no_output": "diagnostic_only",
        "fail_closed": "blocked",
        "integrity_conflict": "failed",
    }.get(result.status, "diagnostic_only")
    diagnostics = result.to_log_dict()
    return build_pipeline_node_result(
        node_name=node_name,
        status=status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=diagnostics,
        artifacts=[
            {
                "artifact_name": node_name,
                "schema_version": diagnostics["schema_version"],
                "content_free": True,
                "present": True,
            }
        ],
    )


__all__ = [
    "EvidenceRuntimeGate",
    "build_evidence_response_capture_node_result",
    "capture_evidence_for_assistant_response_nonstream",
    "capture_evidence_for_user_input",
    "prepare_stream_evidence_response_capture",
    "resolve_evidence_gate",
]
