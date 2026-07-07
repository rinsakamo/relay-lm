"""RelayRUN runtime artifact construction for managed chat completions."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Any

from relaylm.config import RelayLMConfig
from relaylm.routing import ResolvedRoute
from relaylm.relayrun import (
    build_relayrun_node,
    build_relayrun_timing_summary,
    write_relayrun_checkpoint_if_enabled,
)
from relaylm.relayrun_lazy_recovery import (
    build_runtime_checkpoint_lazy_recovery_artifact,
)


def _node_timing_kwargs(timing: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(timing, Mapping):
        return {"started_at": None, "completed_at": None, "duration_ms": None}
    return {
        "started_at": timing.get("started_at"),
        "completed_at": timing.get("completed_at"),
        "duration_ms": timing.get("duration_ms"),
    }


@dataclass
class _ManagedRuntimeArtifactContext:
    """Fields shared by every RelayRUN artifact build for one managed request.

    Only backend_forward_status and the stream/backend-progress flags vary
    across the pending/failed/completed call sites, so this context freezes
    everything else exactly as it was computed by the runtime pipeline.
    """

    config: RelayLMConfig
    request_id: str
    run_id: str
    route: ResolvedRoute
    stream_enabled: bool
    relayrel_relationship_projection: Mapping[str, Any] | None
    relayscn_scene_policy_artifact: Mapping[str, Any] | None
    relayemo_artifact: Mapping[str, Any] | None
    relayint_intent_artifact: Mapping[str, Any] | None
    relaymem_retrieval_artifact: Mapping[str, Any] | None
    runtime_ctx_injection_result: Mapping[str, Any] | None
    runtime_snippet_injection_result: Mapping[str, Any] | None
    relayctx_short_term_runtime_injection_apply_result: Mapping[str, Any] | None
    token_budget_truncation: Mapping[str, Any] | None
    node_timings: Mapping[str, Mapping[str, Any] | None] = field(default_factory=dict)


def _build_relayrun_runtime_artifact_for_context(
    context: _ManagedRuntimeArtifactContext,
    *,
    backend_forward_status: str,
    backend_forward_blocked_reasons: list[str] | None = None,
    backend_forward_timing: Mapping[str, Any] | None = None,
    stream_started: bool | None = None,
    first_token_sent: bool | None = None,
) -> dict[str, Any]:
    node_timings = dict(context.node_timings)
    node_timings["backend_forward"] = backend_forward_timing
    return _build_relayrun_runtime_artifact(
        config=context.config,
        request_id=context.request_id,
        run_id=context.run_id,
        route=context.route,
        stream_enabled=context.stream_enabled,
        relayrel_relationship_projection=context.relayrel_relationship_projection,
        relayscn_scene_policy_artifact=context.relayscn_scene_policy_artifact,
        relayemo_artifact=context.relayemo_artifact,
        relayint_intent_artifact=context.relayint_intent_artifact,
        relaymem_retrieval_artifact=context.relaymem_retrieval_artifact,
        runtime_ctx_injection_result=context.runtime_ctx_injection_result,
        runtime_snippet_injection_result=context.runtime_snippet_injection_result,
        relayctx_short_term_runtime_injection_apply_result=(
            context.relayctx_short_term_runtime_injection_apply_result
        ),
        token_budget_truncation=context.token_budget_truncation,
        node_timings=node_timings,
        backend_forward_status=backend_forward_status,
        backend_forward_blocked_reasons=backend_forward_blocked_reasons,
        stream_started=stream_started,
        first_token_sent=first_token_sent,
    )


def _build_relayrun_runtime_artifact(
    *,
    config: RelayLMConfig,
    request_id: str,
    run_id: str,
    route: ResolvedRoute,
    stream_enabled: bool,
    relayrel_relationship_projection: Mapping[str, Any] | None,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None,
    relayemo_artifact: Mapping[str, Any] | None,
    relayint_intent_artifact: Mapping[str, Any] | None,
    relaymem_retrieval_artifact: Mapping[str, Any] | None,
    runtime_ctx_injection_result: Mapping[str, Any] | None,
    runtime_snippet_injection_result: Mapping[str, Any] | None,
    relayctx_short_term_runtime_injection_apply_result: Mapping[str, Any] | None,
    token_budget_truncation: Mapping[str, Any] | None,
    backend_forward_status: str,
    backend_forward_blocked_reasons: list[str] | None = None,
    node_timings: Mapping[str, Mapping[str, Any] | None] | None = None,
    stream_started: bool | None = None,
    first_token_sent: bool | None = None,
) -> dict[str, Any]:
    timings = node_timings or {}
    node_statuses = [
        build_relayrun_node(
            node_name="request_received",
            node_status="completed",
            **_node_timing_kwargs(timings.get("request_received")),
        ),
        _relayrun_relayrel_node(relayrel_relationship_projection, timing=timings.get("relayrel")),
        _relayrun_relayscn_node(relayscn_scene_policy_artifact, timing=timings.get("relayscn")),
        _relayrun_relayemo_node(
            relayemo_artifact=relayemo_artifact,
            relayemo_enabled=config.relayemo_enabled,
            timing=timings.get("relayemo"),
        ),
        _relayrun_relayint_intent_node(relayint_intent_artifact, timing=timings.get("relayint")),
        _relayrun_relaymem_retrieval_node(
            relaymem_retrieval_artifact, timing=timings.get("relaymem_retrieval")
        ),
        _relayrun_relaymem_runtime_ctx_node(
            runtime_ctx_injection_result=runtime_ctx_injection_result,
            runtime_snippet_injection_result=runtime_snippet_injection_result,
            timing=timings.get("relaymem_runtime_ctx"),
        ),
        _relayrun_relayctx_short_term_injection_node(
            relayctx_short_term_runtime_injection_apply_result,
            timing=timings.get("relayctx_short_term_injection"),
        ),
        _relayrun_token_budget_truncation_node(
            token_budget_truncation, timing=timings.get("token_budget_truncation")
        ),
        build_relayrun_node(
            node_name="backend_forward",
            node_status=_relayrun_backend_forward_status(backend_forward_status),
            blocked_reasons=backend_forward_blocked_reasons,
            fallback_reason=(
                "backend_request_error"
                if backend_forward_status == "failed"
                else None
            ),
            **_node_timing_kwargs(timings.get("backend_forward")),
        ),
    ]
    blocked_reasons = _relayrun_collect_blocked_reasons(node_statuses)
    timing_summary = build_relayrun_timing_summary(node_statuses)
    artifact = build_runtime_checkpoint_lazy_recovery_artifact(
        include_recovery_details=None,
        backend_forward_status=backend_forward_status,
        timing_summary=timing_summary,
        checkpoint_write_enabled=config.relayrun_checkpoint_write_enabled,
        checkpoint_dry_run_only=config.relayrun_checkpoint_dry_run_only,
        request_id=request_id,
        run_id=run_id,
        turn_id=None,
        route_model=route.route_model,
        backend_name=route.backend_name,
        character_id=route.character_id,
        stream_enabled=stream_enabled,
        node_statuses=node_statuses,
        blocked_reasons=blocked_reasons,
        stream_started=stream_started,
        first_token_sent=first_token_sent,
        resume_allowed=False,
        resume_mode="none",
        checkpoint_persisted=False,
        checkpoint_target_root=config.relayrun_checkpoint_root,
        checkpoint_index_enabled=config.relayrun_checkpoint_index_enabled,
        checkpoint_index_dry_run_only=config.relayrun_checkpoint_index_dry_run_only,
        checkpoint_index_max_files=config.relayrun_checkpoint_index_max_files,
        resume_preflight_enabled=config.relayrun_resume_preflight_enabled,
        resume_dry_run_only=config.relayrun_resume_dry_run_only,
        recovery_transition_enabled=config.relayrun_recovery_transition_enabled,
        recovery_transition_dry_run_only=config.relayrun_recovery_transition_dry_run_only,
        waiting_user_contract_enabled=config.relayrun_waiting_user_contract_enabled,
        waiting_user_contract_dry_run_only=config.relayrun_waiting_user_contract_dry_run_only,
        recovery_apply_preflight_enabled=config.relayrun_recovery_apply_preflight_enabled,
        recovery_apply_dry_run_only=config.relayrun_recovery_apply_dry_run_only,
        recovery_response_draft_enabled=config.relayrun_recovery_response_draft_enabled,
        recovery_response_draft_dry_run_only=config.relayrun_recovery_response_draft_dry_run_only,
        visible_recovery_preflight_enabled=config.relayrun_visible_recovery_preflight_enabled,
        visible_recovery_dry_run_only=config.relayrun_visible_recovery_dry_run_only,
        recovery_response_generator_enabled=config.relayrun_recovery_response_generator_enabled,
        recovery_response_generator_dry_run_only=config.relayrun_recovery_response_generator_dry_run_only,
        output_relayscn_recovery_gate_enabled=config.relayrun_output_relayscn_recovery_gate_enabled,
        output_relayscn_recovery_gate_dry_run_only=config.relayrun_output_relayscn_recovery_gate_dry_run_only,
        visible_recovery_apply_preflight_enabled=config.relayrun_visible_recovery_apply_preflight_enabled,
        visible_recovery_apply_preflight_dry_run_only=config.relayrun_visible_recovery_apply_preflight_dry_run_only,
        user_action_dry_run_enabled=config.relayrun_user_action_dry_run_enabled,
        user_action_dry_run_only=config.relayrun_user_action_dry_run_only,
        recovery_transition_created=False,
        applied=False,
    )
    if backend_forward_status == "pending":
        return artifact
    return write_relayrun_checkpoint_if_enabled(
        artifact,
        write_enabled=config.relayrun_checkpoint_write_enabled,
        dry_run_only=config.relayrun_checkpoint_dry_run_only,
    )


def _relayrun_relayscn_node(
    artifact: Mapping[str, Any] | None,
    *,
    timing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return build_relayrun_node(
            node_name="relayscn",
            node_status="failed",
            blocked_reasons=["relayscn_scene_policy_artifact_missing"],
            fallback_reason="relayscn_artifact_missing",
            **_node_timing_kwargs(timing),
        )
    scene_state = artifact.get("scene_state")
    scene_type = scene_state.get("scene_type") if isinstance(scene_state, Mapping) else None
    scene_policy = artifact.get("scene_policy")
    blocked_reasons = _string_list(artifact.get("persistence_block_reasons"))
    blocked_reasons.extend(
        reason
        for reason in _string_list(
            scene_policy.get("persistence_block_reasons")
            if isinstance(scene_policy, Mapping)
            else None
        )
        if reason not in blocked_reasons
    )
    persistence_block = artifact.get("persistence_block") is True
    if isinstance(scene_policy, Mapping) and scene_policy.get("persistence_block") is True:
        persistence_block = True
    if persistence_block and not blocked_reasons:
        if isinstance(scene_type, str) and scene_type:
            blocked_reasons = [f"scene_policy:{scene_type}"]
        else:
            blocked_reasons = ["scene_policy:blocked"]
    status = "blocked" if blocked_reasons else "completed"
    return build_relayrun_node(
        node_name="relayscn",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason="scene_policy_fail_closed" if blocked_reasons else None,
        **_node_timing_kwargs(timing),
    )


def _relayrun_relayrel_node(
    artifact: Mapping[str, Any] | None,
    *,
    timing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return build_relayrun_node(
            node_name="relayrel",
            node_status="failed",
            blocked_reasons=["relayrel_relationship_projection_missing"],
            fallback_reason="relayrel_relationship_projection_missing",
            **_node_timing_kwargs(timing),
        )
    return build_relayrun_node(
        node_name="relayrel", node_status="completed", **_node_timing_kwargs(timing)
    )


def _relayrun_relayemo_node(
    *,
    relayemo_artifact: Mapping[str, Any] | None,
    relayemo_enabled: bool,
    timing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not relayemo_enabled:
        return build_relayrun_node(node_name="relayemo", node_status="skipped")
    if not isinstance(relayemo_artifact, Mapping):
        return build_relayrun_node(
            node_name="relayemo",
            node_status="failed",
            blocked_reasons=["relayemo_artifact_missing"],
            fallback_reason="relayemo_artifact_missing",
            **_node_timing_kwargs(timing),
        )
    fallback_reason = relayemo_artifact.get("fallback_reason")
    blocked_reasons = _string_list(relayemo_artifact.get("blocked_reasons"))
    status = "blocked" if blocked_reasons else "completed"
    return build_relayrun_node(
        node_name="relayemo",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason=fallback_reason if isinstance(fallback_reason, str) else None,
        **_node_timing_kwargs(timing),
    )


def _relayrun_relayint_intent_node(
    artifact: Mapping[str, Any] | None,
    *,
    timing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return build_relayrun_node(
            node_name="relayint",
            node_status="failed",
            blocked_reasons=["relayint_intent_artifact_missing"],
            fallback_reason="relayint_intent_artifact_missing",
            **_node_timing_kwargs(timing),
        )
    blocked_reasons = []
    if artifact.get("unresolved_reference_detected") is True:
        blocked_reasons.append("unresolved_reference_detected")
    mode = artifact.get("mode")
    blocked_reasons.extend(
        reason
        for reason in _string_list(artifact.get("mode_reasons"))
        if reason not in blocked_reasons
        and not (reason == "recovery_scene" and mode == "context_repair")
    )
    status = "blocked" if blocked_reasons else "completed"
    return build_relayrun_node(
        node_name="relayint",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason=(
            str(artifact.get("mode"))
            if blocked_reasons and isinstance(artifact.get("mode"), str)
            else None
        ),
        **_node_timing_kwargs(timing),
    )


def _relayrun_relaymem_retrieval_node(
    artifact: Mapping[str, Any] | None,
    *,
    timing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return build_relayrun_node(
            node_name="relaymem_retrieval",
            node_status="failed",
            blocked_reasons=["relaymem_retrieval_artifact_missing"],
            fallback_reason="relaymem_retrieval_artifact_missing",
            **_node_timing_kwargs(timing),
        )
    blocked_reasons = []
    apply_decision = artifact.get("apply_decision")
    if isinstance(apply_decision, str) and apply_decision.startswith("blocked_"):
        blocked_reasons.append(f"apply_decision:{apply_decision}")
    fallback_reason = artifact.get("fallback_reason")
    snippet_apply_decision = artifact.get("snippet_apply_decision")
    if (
        isinstance(snippet_apply_decision, str)
        and snippet_apply_decision.startswith("blocked_")
    ):
        blocked_reasons.append(f"snippet_apply_decision:{snippet_apply_decision}")
    status = "blocked" if blocked_reasons else "completed"
    return build_relayrun_node(
        node_name="relaymem_retrieval",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason=fallback_reason if isinstance(fallback_reason, str) else None,
        **_node_timing_kwargs(timing),
    )


def _relayrun_relaymem_runtime_ctx_node(
    *,
    runtime_ctx_injection_result: Mapping[str, Any] | None,
    runtime_snippet_injection_result: Mapping[str, Any] | None,
    timing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        not isinstance(runtime_ctx_injection_result, Mapping)
        or not isinstance(runtime_snippet_injection_result, Mapping)
    ):
        return build_relayrun_node(
            node_name="relaymem_runtime_ctx",
            node_status="failed",
            blocked_reasons=["runtime_ctx_or_snippet_result_missing"],
            fallback_reason="runtime_ctx_result_missing",
            **_node_timing_kwargs(timing),
        )
    if (
        runtime_ctx_injection_result.get("applied") is True
        or runtime_snippet_injection_result.get("applied") is True
    ):
        return build_relayrun_node(
            node_name="relaymem_runtime_ctx",
            node_status="completed",
            **_node_timing_kwargs(timing),
        )
    blocked_reasons = _string_list(runtime_snippet_injection_result.get("blocked_reasons"))
    blocked_reasons.extend(
        reason
        for reason in _string_list(runtime_ctx_injection_result.get("blocked_reasons"))
        if reason not in blocked_reasons
    )
    status = "blocked" if blocked_reasons else "skipped"
    return build_relayrun_node(
        node_name="relaymem_runtime_ctx",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason="runtime_ctx_not_applied" if blocked_reasons else None,
        **_node_timing_kwargs(timing),
    )


def _relayrun_relayctx_short_term_injection_node(
    apply_result: Mapping[str, Any] | None,
    *,
    timing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(apply_result, Mapping):
        return build_relayrun_node(
            node_name="relayctx_short_term_injection",
            node_status="skipped",
            **_node_timing_kwargs(timing),
        )
    if apply_result.get("applied") is True:
        return build_relayrun_node(
            node_name="relayctx_short_term_injection",
            node_status="completed",
            **_node_timing_kwargs(timing),
        )
    blocked_reasons = _string_list(apply_result.get("blocked_reasons"))
    status = "blocked" if blocked_reasons else "skipped"
    return build_relayrun_node(
        node_name="relayctx_short_term_injection",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason=(
            "relayctx_short_term_injection_not_applied" if blocked_reasons else None
        ),
        **_node_timing_kwargs(timing),
    )


def _relayrun_token_budget_truncation_node(
    artifact: Mapping[str, Any] | None,
    *,
    timing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(artifact, Mapping):
        return build_relayrun_node(
            node_name="token_budget_truncation",
            node_status="skipped",
            **_node_timing_kwargs(timing),
        )
    blocked_reasons = []
    blocked_reason = artifact.get("blocked_reason")
    if isinstance(blocked_reason, str) and blocked_reason:
        blocked_reasons.append(blocked_reason)
    status = "blocked" if blocked_reasons else "completed"
    return build_relayrun_node(
        node_name="token_budget_truncation",
        node_status=status,
        blocked_reasons=blocked_reasons,
        fallback_reason="token_budget_blocked" if blocked_reasons else None,
        **_node_timing_kwargs(timing),
    )


def _relayrun_backend_forward_status(status: str) -> str:
    if status in {"completed", "failed", "blocked", "skipped"}:
        return status
    return "pending"


def _relayrun_collect_blocked_reasons(node_statuses: list[dict[str, Any]]) -> list[str]:
    blocked_reasons: list[str] = []
    for node in node_statuses:
        if not isinstance(node, Mapping):
            continue
        node_name = node.get("node_name")
        prefix = f"{node_name}:" if isinstance(node_name, str) and node_name else ""
        for reason in _string_list(node.get("blocked_reasons")):
            value = f"{prefix}{reason}" if prefix else reason
            if value not in blocked_reasons:
                blocked_reasons.append(value)
    return blocked_reasons


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]
