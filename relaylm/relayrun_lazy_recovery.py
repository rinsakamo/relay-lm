"""Lazy RelayRUN recovery-detail construction helpers.

This module is side-effect free. It keeps the ordinary runtime path able to
produce a small content-free checkpoint summary without eagerly constructing the
full recovery diagnostic chain. Callers can still force full detail construction
for blocked, failed, checkpoint, or recovery-diagnostics paths.
"""

from __future__ import annotations

from typing import Any, Mapping

from relaylm.relayrun import (
    RUNTIME_CHECKPOINT_NODE_SEQUENCE,
    build_relayrun_checkpoint_persistence_plan,
    build_relayrun_checkpoint_writer_preflight,
    build_runtime_checkpoint_dry_run_artifact,
    new_run_id,
)

RECOVERY_DETAIL_SCHEMA_VERSION = "relayrun.recovery_detail.lazy.v0"

RECOVERY_DETAIL_ARTIFACT_KEYS: tuple[str, ...] = (
    "resume_preflight",
    "checkpoint_index",
    "recovery_transition_artifact",
    "waiting_user_contract",
    "recovery_apply_preflight",
    "recovery_response_draft",
    "visible_recovery_response_preflight",
    "recovery_response_generator",
    "output_relayscn_recovery_gate",
    "visible_recovery_apply_preflight",
    "user_action_contract",
)

_RECOVERY_ENABLED_FLAGS: tuple[str, ...] = (
    "resume_preflight_enabled",
    "recovery_transition_enabled",
    "waiting_user_contract_enabled",
    "recovery_apply_preflight_enabled",
    "recovery_response_draft_enabled",
    "visible_recovery_preflight_enabled",
    "recovery_response_generator_enabled",
    "output_relayscn_recovery_gate_enabled",
    "visible_recovery_apply_preflight_enabled",
    "user_action_dry_run_enabled",
)

_BENIGN_RECOVERY_DETAIL_BLOCKED_REASONS = frozenset(
    {
        "relaymem_retrieval:apply_decision:blocked_no_candidates",
        "relaymem_retrieval:snippet_apply_decision:blocked_no_candidates",
        "relaymem_runtime_ctx:snippet_apply_decision:blocked_no_candidates",
        "relaymem_runtime_ctx:snippet_runtime_injection_plan_preview_empty",
        "relaymem_runtime_ctx:snippet_runtime_injection_plan_blocked",
        "relaymem_retrieval:apply_decision:blocked_scene_policy",
        "relaymem_runtime_ctx:apply_decision:blocked_scene_policy",
        "relaymem_runtime_ctx:ctx_injection_plan_preview_empty",
        "relaymem_runtime_ctx:ctx_injection_plan_blocked",
        "relayscn:scene_policy:recovery",
        "scene_policy:recovery",
        "relayscn:scene_policy:blocked",
        "scene_policy:blocked",
        "apply_decision:blocked_no_candidates",
        "snippet_apply_decision:blocked_no_candidates",
        "snippet_runtime_injection_plan_preview_empty",
        "snippet_runtime_injection_plan_blocked",
        "apply_decision:blocked_scene_policy",
        "ctx_injection_plan_preview_empty",
        "ctx_injection_plan_blocked",
    }
)


def _recovery_detail_blocking_reasons(value: Any) -> tuple[str, ...]:
    return tuple(
        reason
        for reason in _string_tuple(value)
        if reason not in _BENIGN_RECOVERY_DETAIL_BLOCKED_REASONS
    )


def _node_status_requires_recovery_detail(node: Mapping[str, Any]) -> bool:
    status = node.get("node_status")
    node_name = node.get("node_name")

    if status in {"failed", "waiting_user"}:
        return True
    if status != "blocked":
        return False

    # Ordinary RelaySCN / RelayMEM policy and no-candidate blocks are still
    # represented in the lightweight runtime checkpoint projection. They should
    # not automatically expand the full recovery-detail chain; explicit recovery
    # smokes and future recovery features opt in through recovery flags.
    if node_name in {"relayscn", "relaymem_retrieval", "relaymem_runtime_ctx"}:
        return False

    if node_name not in {"relayref", "relayint", "backend_forward"}:
        return False

    raw_reasons = _string_tuple(node.get("blocked_reasons"))
    if _recovery_detail_blocking_reasons(raw_reasons):
        return True
    if raw_reasons:
        return False
    return True






def build_runtime_checkpoint_lazy_recovery_artifact(
    *,
    include_recovery_details: bool | None = None,
    checkpoint_write_enabled: bool = False,
    checkpoint_dry_run_only: bool = True,
    backend_forward_status: str | None = None,
    recovery_detail_reason: str | None = None,
    **checkpoint_kwargs: Any,
) -> dict[str, Any]:
    """Build a RelayRUN runtime checkpoint artifact with lazy recovery detail.

    The helper preserves the existing full-detail helper when detail is required.
    On the ordinary completed path, it constructs only the content-free summary
    fields needed by runtime diagnostics and leaves heavyweight recovery-chain
    artifacts unconstructed as ``None``.
    """

    required, required_reasons = relayrun_recovery_detail_required(
        include_recovery_details=include_recovery_details,
        checkpoint_write_enabled=checkpoint_write_enabled,
        checkpoint_dry_run_only=checkpoint_dry_run_only,
        backend_forward_status=backend_forward_status,
        **checkpoint_kwargs,
    )
    reason = recovery_detail_reason or _recovery_detail_reason(
        required=required,
        required_reasons=required_reasons,
        include_recovery_details=include_recovery_details,
    )

    if required:
        artifact = build_runtime_checkpoint_dry_run_artifact(**checkpoint_kwargs)
        artifact["recovery_detail"] = _recovery_detail_summary(
            constructed=True,
            reason=reason,
            required_reasons=required_reasons,
        )
        return artifact

    artifact = _build_minimal_runtime_checkpoint_artifact(**checkpoint_kwargs)
    artifact["recovery_detail"] = _recovery_detail_summary(
        constructed=False,
        reason=reason,
        required_reasons=required_reasons,
    )
    return artifact


def relayrun_recovery_detail_required(
    *,
    include_recovery_details: bool | None = None,
    checkpoint_write_enabled: bool = False,
    checkpoint_dry_run_only: bool = True,
    backend_forward_status: str | None = None,
    **checkpoint_kwargs: Any,
) -> tuple[bool, tuple[str, ...]]:
    """Return whether full recovery detail must be constructed.

    The decision is content-free and based only on status values, reason IDs, and
    explicit diagnostics/checkpoint gates.
    """

    if include_recovery_details is True:
        return True, ("explicit_include_recovery_details",)
    if include_recovery_details is False:
        return False, ("explicit_skip_recovery_details",)

    reasons: list[str] = []
    if backend_forward_status in {"failed", "blocked"}:
        reasons.append(f"backend_forward_status:{backend_forward_status}")

    blocked_reasons = _recovery_detail_blocking_reasons(
        checkpoint_kwargs.get("blocked_reasons")
    )
    if blocked_reasons:
        reasons.append("blocked_reasons_present")

    node_statuses = checkpoint_kwargs.get("node_statuses")
    if isinstance(node_statuses, list | tuple):
        for node in node_statuses:
            if not isinstance(node, Mapping):
                continue
            if _node_status_requires_recovery_detail(node):
                status = node.get("node_status")
                node_name = node.get("node_name")
                if isinstance(node_name, str) and node_name:
                    reasons.append(f"node_status:{node_name}:{status}")
                else:
                    reasons.append(f"node_status:{status}")

    if checkpoint_write_enabled:
        reasons.append(
            "checkpoint_write_requested"
            if not checkpoint_dry_run_only
            else "checkpoint_write_dry_run_requested"
        )

    if checkpoint_kwargs.get("checkpoint_index_enabled") is True:
        reasons.append(
            "checkpoint_index_requested"
            if checkpoint_kwargs.get("checkpoint_index_dry_run_only") is False
            else "checkpoint_index_dry_run_requested"
        )

    for flag_name in _RECOVERY_ENABLED_FLAGS:
        if checkpoint_kwargs.get(flag_name) is True:
            reasons.append(flag_name)

    if checkpoint_kwargs.get("recovery_transition_created") is True:
        reasons.append("recovery_transition_created")
    if checkpoint_kwargs.get("applied") is True:
        reasons.append("runtime_apply_state_present")

    unique_reasons = _unique_string_tuple(reasons)
    return bool(unique_reasons), unique_reasons


def _build_minimal_runtime_checkpoint_artifact(**checkpoint_kwargs: Any) -> dict[str, Any]:
    request_id = str(checkpoint_kwargs["request_id"])
    safe_run_id = checkpoint_kwargs.get("run_id") or new_run_id()
    turn_id = checkpoint_kwargs.get("turn_id")
    checkpoint_target_root = str(
        checkpoint_kwargs.get("checkpoint_target_root") or ".relayrun/checkpoints"
    )
    checkpoint_persisted = checkpoint_kwargs.get("checkpoint_persisted") is True
    checkpoint_persistence_plan = build_relayrun_checkpoint_persistence_plan(
        run_id=safe_run_id,
        turn_id=turn_id if isinstance(turn_id, str) else None,
        request_id=request_id,
        target_root=checkpoint_target_root,
        checkpoint_persisted=checkpoint_persisted,
    )
    checkpoint_writer_preflight = build_relayrun_checkpoint_writer_preflight(
        target_root=str(checkpoint_persistence_plan["target_root"]),
        target_path_preview=str(checkpoint_persistence_plan["target_path_preview"]),
    )

    safe_nodes = []
    node_statuses = checkpoint_kwargs.get("node_statuses")
    if isinstance(node_statuses, list | tuple):
        for node in node_statuses:
            if isinstance(node, dict):
                safe_nodes.append(dict(node))

    safe_blocked_reasons = list(_string_tuple(checkpoint_kwargs.get("blocked_reasons")))
    resume_mode = checkpoint_kwargs.get("resume_mode")
    if not isinstance(resume_mode, str) or not resume_mode:
        resume_mode = "none"

    artifact: dict[str, Any] = {
        "schema_version": "relayrun.runtime_checkpoint.v0",
        "diagnostics_only": True,
        "applied": checkpoint_kwargs.get("applied") is True,
        "run_id": safe_run_id,
        "request_id": request_id,
        "turn_id": turn_id,
        "route_model": checkpoint_kwargs.get("route_model"),
        "backend_name": checkpoint_kwargs.get("backend_name"),
        "character_id": checkpoint_kwargs.get("character_id"),
        "stream_enabled": checkpoint_kwargs.get("stream_enabled"),
        "run_status": "diagnostics_only",
        "node_sequence": list(RUNTIME_CHECKPOINT_NODE_SEQUENCE),
        "node_statuses": safe_nodes,
        "stream_started": checkpoint_kwargs.get("stream_started"),
        "first_token_sent": checkpoint_kwargs.get("first_token_sent"),
        "resume_allowed": checkpoint_kwargs.get("resume_allowed") is True,
        "resume_mode": resume_mode,
        "checkpoint_persisted": checkpoint_persisted,
        "checkpoint_write_attempted": False,
        "checkpoint_writer_failed": False,
        "persisted_path": None,
        "persisted_bytes": None,
        "content_free": True,
        "checkpoint_persistence_plan": checkpoint_persistence_plan,
        "checkpoint_writer_preflight": checkpoint_writer_preflight,
        "recovery_transition_created": checkpoint_kwargs.get("recovery_transition_created")
        is True,
        "blocked_reasons": safe_blocked_reasons,
        "timing_summary": (
            dict(checkpoint_kwargs["timing_summary"])
            if isinstance(checkpoint_kwargs.get("timing_summary"), Mapping)
            else None
        ),
    }
    for key in RECOVERY_DETAIL_ARTIFACT_KEYS:
        artifact[key] = None
    return artifact


def _recovery_detail_summary(
    *,
    constructed: bool,
    reason: str,
    required_reasons: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": RECOVERY_DETAIL_SCHEMA_VERSION,
        "constructed": bool(constructed),
        "reason": reason,
        "required_reasons": list(required_reasons),
        "content_free": True,
        "contains_user_content": False,
        "contains_backend_payload": False,
        "contains_response_text": False,
        "diagnostics_only": True,
    }


def _recovery_detail_reason(
    *,
    required: bool,
    required_reasons: tuple[str, ...],
    include_recovery_details: bool | None,
) -> str:
    if include_recovery_details is True:
        return "explicit_include_recovery_details"
    if include_recovery_details is False:
        return "explicit_skip_recovery_details"
    if required:
        return required_reasons[0] if required_reasons else "recovery_detail_required"
    return "ordinary_path_no_blocked_or_checkpoint_need"


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str) and item)


def _unique_string_tuple(values: list[str]) -> tuple[str, ...]:
    output: list[str] = []
    for value in values:
        if value and value not in output:
            output.append(value)
    return tuple(output)
