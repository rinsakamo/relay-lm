#!/usr/bin/env python3
"""Smoke tests for lazy RelayRUN recovery-detail construction."""

from __future__ import annotations

from relaylm.relayrun import build_relayrun_node
from relaylm.relayrun_lazy_recovery import (
    RECOVERY_DETAIL_ARTIFACT_KEYS,
    build_runtime_checkpoint_lazy_recovery_artifact,
    relayrun_recovery_detail_required,
)


def _base_kwargs() -> dict[str, object]:
    return {
        "request_id": "req-lazy-smoke",
        "run_id": "run-lazy-smoke",
        "turn_id": None,
        "route_model": "relaylm-companion",
        "backend_name": "lmstudio",
        "character_id": "default",
        "stream_enabled": False,
        "node_statuses": [
            build_relayrun_node(node_name="request_received", node_status="completed"),
            build_relayrun_node(node_name="backend_forward", node_status="completed"),
        ],
        "blocked_reasons": [],
        "stream_started": False,
        "first_token_sent": False,
        "resume_allowed": False,
        "resume_mode": "none",
        "checkpoint_persisted": False,
        "checkpoint_target_root": ".relayrun/checkpoints",
        "checkpoint_index_enabled": False,
        "checkpoint_index_dry_run_only": True,
        "checkpoint_index_max_files": 100,
        "resume_preflight_enabled": False,
        "resume_dry_run_only": True,
        "recovery_transition_enabled": False,
        "recovery_transition_dry_run_only": True,
        "waiting_user_contract_enabled": False,
        "waiting_user_contract_dry_run_only": True,
        "recovery_apply_preflight_enabled": False,
        "recovery_apply_dry_run_only": True,
        "recovery_response_draft_enabled": False,
        "recovery_response_draft_dry_run_only": True,
        "visible_recovery_preflight_enabled": False,
        "visible_recovery_dry_run_only": True,
        "recovery_response_generator_enabled": False,
        "recovery_response_generator_dry_run_only": True,
        "output_relayscn_recovery_gate_enabled": False,
        "output_relayscn_recovery_gate_dry_run_only": True,
        "visible_recovery_apply_preflight_enabled": False,
        "visible_recovery_apply_preflight_dry_run_only": True,
        "user_action_dry_run_enabled": False,
        "user_action_dry_run_only": True,
        "recovery_transition_created": False,
        "applied": False,
    }


def assert_lazy_ordinary_path() -> None:
    artifact = build_runtime_checkpoint_lazy_recovery_artifact(
        backend_forward_status="completed",
        **_base_kwargs(),
    )
    detail = artifact.get("recovery_detail")
    assert isinstance(detail, dict)
    assert detail["constructed"] is False
    assert detail["reason"] == "ordinary_path_no_blocked_or_checkpoint_need"
    assert detail["content_free"] is True
    assert artifact["content_free"] is True
    assert artifact["node_statuses"]
    assert artifact["blocked_reasons"] == []
    assert artifact["checkpoint_persistence_plan"]["diagnostics_only"] is True
    assert artifact["checkpoint_writer_preflight"]["diagnostics_only"] is True
    for key in RECOVERY_DETAIL_ARTIFACT_KEYS:
        assert key in artifact, key
        assert artifact[key] is None, key


def assert_blocked_path_builds_full_detail() -> None:
    kwargs = _base_kwargs()
    kwargs["node_statuses"] = [
        build_relayrun_node(node_name="relayref", node_status="blocked", blocked_reasons=["unresolved_reference_detected"]),
        build_relayrun_node(node_name="backend_forward", node_status="pending"),
    ]
    kwargs["blocked_reasons"] = ["relayref:unresolved_reference_detected"]
    artifact = build_runtime_checkpoint_lazy_recovery_artifact(
        backend_forward_status="blocked",
        **kwargs,
    )
    detail = artifact.get("recovery_detail")
    assert isinstance(detail, dict)
    assert detail["constructed"] is True
    assert "blocked_reasons_present" in detail["required_reasons"]
    assert isinstance(artifact.get("recovery_transition_artifact"), dict)
    assert isinstance(artifact.get("waiting_user_contract"), dict)
    assert artifact["content_free"] is True


def assert_backend_failed_path_builds_full_detail() -> None:
    kwargs = _base_kwargs()
    kwargs["node_statuses"] = [
        build_relayrun_node(node_name="backend_forward", node_status="failed", blocked_reasons=["BackendRequestError"]),
    ]
    artifact = build_runtime_checkpoint_lazy_recovery_artifact(
        backend_forward_status="failed",
        **kwargs,
    )
    detail = artifact.get("recovery_detail")
    assert isinstance(detail, dict)
    assert detail["constructed"] is True
    assert "backend_forward_status:failed" in detail["required_reasons"]
    assert isinstance(artifact.get("recovery_apply_preflight"), dict)


def assert_explicit_override_is_respected() -> None:
    required, reasons = relayrun_recovery_detail_required(
        include_recovery_details=False,
        backend_forward_status="failed",
        **_base_kwargs(),
    )
    assert required is False
    assert reasons == ("explicit_skip_recovery_details",)

    artifact = build_runtime_checkpoint_lazy_recovery_artifact(
        include_recovery_details=True,
        backend_forward_status="completed",
        **_base_kwargs(),
    )
    detail = artifact.get("recovery_detail")
    assert isinstance(detail, dict)
    assert detail["constructed"] is True
    assert detail["reason"] == "explicit_include_recovery_details"


def assert_checkpoint_and_recovery_flags_require_detail() -> None:
    required, reasons = relayrun_recovery_detail_required(
        checkpoint_write_enabled=True,
        checkpoint_dry_run_only=False,
        backend_forward_status="completed",
        **_base_kwargs(),
    )
    assert required is True
    assert "checkpoint_write_requested" in reasons

    kwargs = _base_kwargs()
    kwargs["recovery_transition_enabled"] = True
    required, reasons = relayrun_recovery_detail_required(
        backend_forward_status="completed",
        **kwargs,
    )
    assert required is True
    assert "recovery_transition_enabled" in reasons


def main() -> None:
    assert_lazy_ordinary_path()
    assert_blocked_path_builds_full_detail()
    assert_backend_failed_path_builds_full_detail()
    assert_explicit_override_is_respected()
    assert_checkpoint_and_recovery_flags_require_detail()
    print("RelayRUN lazy recovery detail smoke passed")


if __name__ == "__main__":
    main()
