"""Runtime boundary for minimal non-streaming RelayCTX Unpack."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from relaylm.relayctx_unpack import RelayCTXUnpackResult, unpack_relayctx_response_text


@dataclass(frozen=True)
class RelayCTXUnpackRuntimeResult:
    """One runtime Unpack outcome without persistence or routing side effects."""

    response_body: Any
    node_result: PipelineNodeResult
    ctx_working_update_candidate: dict[str, Any] | None
    applied_to_response: bool


def apply_relayctx_unpack_runtime(
    body: Any,
    *,
    status_code: int,
    apply_enabled: bool,
    dry_run_only: bool,
    max_update_chars: int,
) -> RelayCTXUnpackRuntimeResult:
    """Run non-stream Unpack against one successful chat-completion response.

    Only a single OpenAI-compatible assistant message with string ``content`` is
    supported in Phase 5-B. Unsupported or failed backend responses are preserved
    byte-for-structure and produce a content-free skipped node result.
    """

    if not 200 <= int(status_code) < 300:
        return _skipped_result(
            body,
            decision="backend_status_not_success",
            blocked_reasons=("backend_status_not_success",),
            apply_enabled=apply_enabled,
            dry_run_only=dry_run_only,
        )

    content_path = _resolve_single_assistant_content(body)
    if content_path is None:
        return _skipped_result(
            body,
            decision="response_shape_unsupported",
            blocked_reasons=("response_shape_unsupported",),
            apply_enabled=apply_enabled,
            dry_run_only=dry_run_only,
        )

    _, _, content = content_path
    unpack_result = unpack_relayctx_response_text(
        content,
        max_update_chars=max_update_chars,
    )
    candidate = (
        deepcopy(unpack_result.ctx_working_update)
        if unpack_result.update_accepted
        and isinstance(unpack_result.ctx_working_update, dict)
        else None
    )

    can_apply_visible_text = (
        apply_enabled
        and not dry_run_only
        and unpack_result.marker_present
        and bool(unpack_result.user_visible_text)
        and unpack_result.status in {"structured_update", "update_blocked"}
    )

    response_body = body
    if can_apply_visible_text:
        response_body = deepcopy(body)
        resolved_copy = _resolve_single_assistant_content(response_body)
        if resolved_copy is None:
            return _skipped_result(
                body,
                decision="response_copy_shape_changed",
                blocked_reasons=("response_copy_shape_changed",),
                apply_enabled=apply_enabled,
                dry_run_only=dry_run_only,
            )
        choice_index, _, _ = resolved_copy
        response_body["choices"][choice_index]["message"]["content"] = (
            unpack_result.user_visible_text
        )

    node_result = _build_runtime_node_result(
        unpack_result,
        apply_enabled=apply_enabled,
        dry_run_only=dry_run_only,
        applied_to_response=can_apply_visible_text,
        candidate_present=candidate is not None,
    )
    return RelayCTXUnpackRuntimeResult(
        response_body=response_body,
        node_result=node_result,
        ctx_working_update_candidate=candidate,
        applied_to_response=can_apply_visible_text,
    )


def _resolve_single_assistant_content(
    body: Any,
) -> tuple[int, Mapping[str, Any], str] | None:
    if not isinstance(body, Mapping):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        return None
    choice = choices[0]
    if not isinstance(choice, Mapping):
        return None
    message = choice.get("message")
    if not isinstance(message, Mapping):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    return 0, message, content


def _build_runtime_node_result(
    unpack_result: RelayCTXUnpackResult,
    *,
    apply_enabled: bool,
    dry_run_only: bool,
    applied_to_response: bool,
    candidate_present: bool,
) -> PipelineNodeResult:
    if unpack_result.status == "empty_response":
        status = "failed"
        decision = "empty_response"
    elif unpack_result.status == "update_blocked":
        status = "blocked"
        decision = (
            "blocked_update_visible_text_applied"
            if applied_to_response
            else "blocked_update_dry_run"
        )
    elif applied_to_response:
        status = "applied"
        decision = "visible_text_applied"
    elif unpack_result.status == "structured_update":
        status = "diagnostic_only"
        decision = "structured_update_dry_run"
    else:
        status = "diagnostic_only"
        decision = "plain_text_no_change"

    diagnostics = unpack_result.to_log_dict()
    diagnostics.update(
        {
            "runtime_schema_version": "relayctx_unpack_runtime.v0",
            "apply_enabled": bool(apply_enabled),
            "dry_run_only": bool(dry_run_only),
            "applied_to_response": applied_to_response,
            "candidate_present": candidate_present,
            "candidate_persistence_allowed": False,
            "response_shape_supported": True,
        }
    )
    return build_pipeline_node_result(
        node_name="relayctx_unpack",
        status=status,
        decision=decision,
        blocked_reasons=unpack_result.blocked_reasons,
        diagnostics=diagnostics,
        artifacts=[
            {
                "artifact_name": "relayctx_unpack_runtime_result",
                "schema_version": "relayctx_unpack_runtime.v0",
                "present": True,
                "content_free": True,
                "applied_to_response": applied_to_response,
                "candidate_present": candidate_present,
                "persistence_allowed": False,
            }
        ],
    )


def _skipped_result(
    body: Any,
    *,
    decision: str,
    blocked_reasons: tuple[str, ...],
    apply_enabled: bool,
    dry_run_only: bool,
) -> RelayCTXUnpackRuntimeResult:
    node_result = build_pipeline_node_result(
        node_name="relayctx_unpack",
        status="skipped",
        decision=decision,
        blocked_reasons=blocked_reasons,
        diagnostics={
            "runtime_schema_version": "relayctx_unpack_runtime.v0",
            "apply_enabled": bool(apply_enabled),
            "dry_run_only": bool(dry_run_only),
            "applied_to_response": False,
            "candidate_present": False,
            "candidate_persistence_allowed": False,
            "response_shape_supported": False,
            "content_free": True,
        },
        artifacts=[
            {
                "artifact_name": "relayctx_unpack_runtime_result",
                "schema_version": "relayctx_unpack_runtime.v0",
                "present": True,
                "content_free": True,
                "applied_to_response": False,
                "candidate_present": False,
                "persistence_allowed": False,
            }
        ],
    )
    return RelayCTXUnpackRuntimeResult(
        response_body=body,
        node_result=node_result,
        ctx_working_update_candidate=None,
        applied_to_response=False,
    )
