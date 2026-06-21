"""Smoke coverage for the Phase 6-A1 RelaySLP job-admission helper."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from relaylm.relaymem_slp_job_admission import (
    build_relaymem_slp_job_admission_preflight,
)


def _shape(
    *,
    source_event_id: bool = True,
    run_id: bool = True,
    session_id: bool = True,
    turn_index: bool = True,
) -> dict[str, bool]:
    return {
        "source_event_id_present": source_event_id,
        "run_id_present": run_id,
        "session_id_present": session_id,
        "turn_index_present": turn_index,
    }


def _lineage(**overrides: Any) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "schema_version": "relaymem.primary_source_lineage.v0",
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "source_event_kind": "turn",
        "namespace": "default",
        "valid": True,
        "lineage_fingerprint": "a" * 64,
        "lineage_shape": _shape(),
        "blocked_reasons": [],
    }
    artifact.update(overrides)
    return artifact


def _valid(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "enabled": True,
        "dry_run_only": True,
        "enqueue_enabled": False,
        "trigger_mode": "turn_end",
        "processing_stage": "primary_formation",
        "run_id": "run-1",
        "turn_index": 4,
        "session_id": "session-1",
        "namespace": "default",
        "source_event_kind": "turn",
        "source_lineage_artifact": _lineage(),
        "source_count": 1,
        "visible_response_finalized": True,
        "runtime_terminal_status": "completed",
        "persistence_policy_status": "allowed",
    }
    values.update(overrides)
    return build_relaymem_slp_job_admission_preflight(**values)


def _contains_value(value: Any, target: Any) -> bool:
    if value == target:
        return True
    if isinstance(value, dict):
        return any(_contains_value(item, target) for item in value.values())
    if isinstance(value, list):
        return any(_contains_value(item, target) for item in value)
    return False


def main() -> None:
    disabled = build_relaymem_slp_job_admission_preflight()
    assert disabled["admission_status"] == "blocked"
    assert "feature_disabled" in disabled["blocked_reasons"]

    dry_run = _valid()
    assert dry_run["admission_status"] == "admitted_dry_run"
    assert dry_run["source_reference_valid"] is True
    assert dry_run["queue_io_performed"] is False
    assert dry_run["enqueued"] is False
    assert dry_run["worker_invoked"] is False
    assert dry_run["invokes_slp"] is False
    assert dry_run["writes_memory"] is False
    assert dry_run["mutates_soul"] is False
    assert dry_run["changes_visible_response"] is False

    enqueue_eligible = _valid(dry_run_only=False, enqueue_enabled=True)
    assert enqueue_eligible["admission_status"] == "eligible_for_enqueue"
    assert enqueue_eligible["enqueue_eligible"] is True
    assert enqueue_eligible["enqueued"] is False

    enqueue_blocked = _valid(dry_run_only=False, enqueue_enabled=False)
    assert enqueue_blocked["admission_status"] == "blocked"
    assert "enqueue_gate_disabled" in enqueue_blocked["blocked_reasons"]

    no_sources = _valid(source_count=0, source_lineage_artifact=None)
    assert no_sources["admission_status"] == "skipped"
    assert no_sources["source_reference_valid"] is False

    for trigger in (
        "session_end",
        "communication_end",
        "scheduled_consolidation",
        "recovery_followup",
        "lab_memory_operation",
        "unknown",
    ):
        result = _valid(trigger_mode=trigger)
        assert result["admission_status"] == "blocked"

    for stage in ("secondary_consolidation", "memory_operation", "lint", "unknown"):
        result = _valid(processing_stage=stage)
        assert result["admission_status"] == "blocked"

    assert "run_id_invalid" in _valid(run_id="raw user text has spaces")[
        "blocked_reasons"
    ]
    assert "turn_index_required_for_turn_end" in _valid(turn_index=None)[
        "blocked_reasons"
    ]
    assert "turn_index_invalid" in _valid(turn_index=-1)["blocked_reasons"]
    assert "namespace_invalid" in _valid(namespace="bad namespace")[
        "blocked_reasons"
    ]
    assert "source_count_invalid" in _valid(source_count=True)["blocked_reasons"]
    assert "source_count_limit_exceeded" in _valid(source_count=33)[
        "blocked_reasons"
    ]

    assert "visible_response_not_finalized" in _valid(
        visible_response_finalized=False
    )["blocked_reasons"]
    explicit = _valid(
        trigger_mode="explicit_memory_request",
        turn_index=None,
        visible_response_finalized=False,
    )
    assert explicit["admission_status"] == "admitted_dry_run"

    for runtime_status in (
        "blocked",
        "failed",
        "waiting_user",
        "recovery_pending",
        "unresolved_recovery",
    ):
        result = _valid(runtime_terminal_status=runtime_status)
        assert result["admission_status"] == "blocked"
        assert any(
            reason.startswith("runtime_status_blocks_admission:")
            for reason in result["blocked_reasons"]
        )

    held = _valid(persistence_policy_status="review_required")
    assert held["admission_status"] == "held"
    assert held["retry_class"] == "policy_hold"
    for policy_status in (
        "explicit_approval_required",
        "blocked",
        "never_auto_promote",
    ):
        result = _valid(persistence_policy_status=policy_status)
        assert result["admission_status"] == "blocked"

    assert "source_lineage_missing" in _valid(source_lineage_artifact=None)[
        "blocked_reasons"
    ]
    assert "source_lineage_schema_mismatch" in _valid(
        source_lineage_artifact=_lineage(schema_version="unknown.v0")
    )["blocked_reasons"]
    assert "source_lineage_namespace_mismatch" in _valid(
        source_lineage_artifact=_lineage(namespace="other")
    )["blocked_reasons"]
    assert "source_lineage_event_kind_mismatch" in _valid(
        source_lineage_artifact=_lineage(source_event_kind="session")
    )["blocked_reasons"]
    assert "source_lineage_fingerprint_invalid" in _valid(
        source_lineage_artifact=_lineage(lineage_fingerprint="not-a-hash")
    )["blocked_reasons"]

    forged_shape = _lineage(
        lineage_shape=_shape(
            source_event_id=False,
            run_id=False,
            session_id=False,
            turn_index=False,
        )
    )
    forged_result = _valid(source_lineage_artifact=forged_shape)
    assert forged_result["admission_status"] == "blocked"
    assert forged_result["source_reference_valid"] is False
    assert "source_lineage_missing" in forged_result["blocked_reasons"]

    source_event_identity = _valid(
        source_lineage_artifact=_lineage(
            lineage_shape=_shape(
                source_event_id=True,
                run_id=False,
                session_id=False,
                turn_index=False,
            )
        )
    )
    assert source_event_identity["source_reference_valid"] is True
    assert source_event_identity["admission_status"] == "admitted_dry_run"

    turn_run_identity = _valid(
        source_lineage_artifact=_lineage(
            lineage_shape=_shape(
                source_event_id=False,
                run_id=True,
                session_id=False,
                turn_index=True,
            )
        )
    )
    assert turn_run_identity["source_reference_valid"] is True

    turn_session_identity = _valid(
        source_lineage_artifact=_lineage(
            lineage_shape=_shape(
                source_event_id=False,
                run_id=False,
                session_id=True,
                turn_index=True,
            )
        )
    )
    assert turn_session_identity["source_reference_valid"] is True

    turn_without_index = _valid(
        source_lineage_artifact=_lineage(
            lineage_shape=_shape(
                source_event_id=False,
                run_id=True,
                session_id=False,
                turn_index=False,
            )
        )
    )
    assert turn_without_index["source_reference_valid"] is False
    assert "source_lineage_missing" in turn_without_index["blocked_reasons"]

    session_identity = _valid(
        trigger_mode="session_end",
        source_event_kind="session",
        source_lineage_artifact=_lineage(
            source_event_kind="session",
            lineage_shape=_shape(
                source_event_id=False,
                run_id=False,
                session_id=True,
                turn_index=False,
            ),
        ),
    )
    assert session_identity["source_reference_valid"] is True
    assert "trigger_mode_unsupported" in session_identity["blocked_reasons"]

    injected = _lineage()
    injected["raw_user_text"] = "private"
    injection_result = _valid(source_lineage_artifact=injected)
    assert injection_result["admission_status"] == "blocked"
    assert "source_lineage_unexpected_field" in injection_result["blocked_reasons"]

    nested_injected = deepcopy(_lineage())
    nested_injected["lineage_shape"]["prompt_text"] = True
    nested_result = _valid(source_lineage_artifact=nested_injected)
    assert nested_result["admission_status"] == "blocked"
    assert any(
        reason
        in {
            "source_lineage_content_field_forbidden",
            "source_lineage_shape_unexpected_field",
        }
        for reason in nested_result["blocked_reasons"]
    )

    projection = dry_run["projection"]
    assert projection["content_free"] is True
    assert projection["content_included"] is False
    assert projection["raw_text_included"] is False
    assert projection["runtime_private_reference_included"] is False
    assert projection["lineage_fingerprint_included"] is False
    assert projection["dispatch_idempotency_key_included"] is False
    assert projection["memory_write_idempotency_key_included"] is False
    assert _contains_value(projection, "run-1") is False
    assert _contains_value(projection, "session-1") is False
    assert _contains_value(projection, "a" * 64) is False
    assert dry_run["dispatch_idempotency_key"] == ""
    assert dry_run["memory_write_idempotency_key"] == ""

    print("RelayMEM RelaySLP job-admission smoke passed")


if __name__ == "__main__":
    main()
