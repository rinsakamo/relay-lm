"""Smoke coverage for the Phase 6-A2 RelaySLP response handoff."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from relaylm.relaymem_slp_job_admission import (
    build_relaymem_slp_job_admission_preflight,
)
from relaylm.relaymem_slp_response_handoff import (
    build_relaymem_slp_response_finalization_handoff,
    build_relaymem_slp_response_handoff_node_result,
)


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
        "lineage_shape": {
            "source_event_id_present": True,
            "run_id_present": True,
            "session_id_present": True,
            "turn_index_present": True,
        },
        "blocked_reasons": [],
    }
    artifact.update(overrides)
    return artifact


def _admission(**overrides: Any) -> dict[str, Any]:
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
    disabled = build_relaymem_slp_response_finalization_handoff(
        _admission(),
        enabled=False,
        response_finalized=True,
    )
    assert disabled.status == "disabled"
    assert disabled.response_finalized is True
    assert disabled.candidate_created is False
    assert disabled.to_runtime_dict()["response_finalized"] is True
    assert disabled.to_log_dict()["response_finalized"] is True

    invalid_gate = build_relaymem_slp_response_finalization_handoff(
        _admission(),
        enabled=1,
        response_finalized=True,
    )
    assert invalid_gate.status == "invalid_input"
    assert "enabled_invalid" in invalid_gate.blocked_reasons

    invalid_finalization = build_relaymem_slp_response_finalization_handoff(
        _admission(),
        enabled=True,
        response_finalized=1,
    )
    assert invalid_finalization.status == "invalid_input"
    assert invalid_finalization.response_finalized is False
    assert "response_finalized_invalid" in invalid_finalization.blocked_reasons

    dry_run = build_relaymem_slp_response_finalization_handoff(
        _admission(),
        enabled=True,
        dry_run_only=True,
        response_finalized=True,
    )
    assert dry_run.status == "dry_run_candidate"
    assert dry_run.response_finalized is True
    assert dry_run.candidate_created is True
    assert dry_run.candidate_count == 1
    runtime = dry_run.to_runtime_dict()
    assert runtime["response_finalized"] is True
    candidate = runtime["candidate"]
    assert isinstance(candidate, dict)
    assert candidate["schema_version"] == "relaymem.slp_enqueue_candidate.v0"
    assert candidate["run_id"] == "run-1"
    assert candidate["turn_index"] == 4
    assert candidate["session_id"] == "session-1"
    assert candidate["namespace"] == "default"
    assert candidate["source_lineage_fingerprint"] == "a" * 64
    assert candidate["enqueue_requested"] is False
    assert candidate["queue_io_performed"] is False
    assert candidate["enqueued"] is False
    assert candidate["worker_invoked"] is False
    assert candidate["invokes_slp"] is False
    assert candidate["writes_memory"] is False
    assert candidate["mutates_soul"] is False
    assert candidate["changes_visible_response"] is False
    assert candidate["dispatch_idempotency_key"] == ""
    assert candidate["memory_write_idempotency_key"] == ""

    projection = dry_run.to_log_dict()
    assert projection["schema_version"] == "relaymem.slp_response_handoff_projection.v0"
    assert projection["content_free"] is True
    assert projection["content_included"] is False
    assert projection["raw_text_included"] is False
    assert projection["response_finalized"] is True
    assert projection["runtime_private_candidate_included"] is False
    assert projection["source_lineage_fingerprint_included"] is False
    assert projection["dispatch_idempotency_key_included"] is False
    assert projection["memory_write_idempotency_key_included"] is False
    assert _contains_value(projection, "run-1") is False
    assert _contains_value(projection, "session-1") is False
    assert _contains_value(projection, "a" * 64) is False

    node_result = build_relaymem_slp_response_handoff_node_result(dry_run)
    assert node_result.node_name == "relaymem_slp_response_handoff"
    assert node_result.status == "diagnostic_only"
    assert node_result.decision == "dry_run_candidate"
    assert node_result.artifacts[0]["candidate_omitted"] is True
    assert node_result.artifacts[0]["queue_io_performed"] is False
    assert _contains_value(node_result.to_log_dict(), "run-1") is False
    assert _contains_value(node_result.to_log_dict(), "a" * 64) is False

    eligible_source = _admission(
        dry_run_only=False,
        enqueue_enabled=True,
    )
    assert eligible_source["admission_status"] == "eligible_for_enqueue"
    eligible = build_relaymem_slp_response_finalization_handoff(
        eligible_source,
        enabled=True,
        dry_run_only=True,
        response_finalized=True,
    )
    assert eligible.status == "dry_run_candidate"
    assert eligible.candidate_created is True
    assert eligible.candidate is not None
    assert eligible.candidate.source_admission_status == "eligible_for_enqueue"

    not_finalized = build_relaymem_slp_response_finalization_handoff(
        _admission(),
        enabled=True,
        response_finalized=False,
    )
    assert not_finalized.status == "blocked"
    assert not_finalized.response_finalized is False
    assert not_finalized.to_log_dict()["response_finalized"] is False
    assert "response_not_finalized" in not_finalized.blocked_reasons
    assert not_finalized.candidate_created is False

    non_dry_run = build_relaymem_slp_response_finalization_handoff(
        _admission(),
        enabled=True,
        dry_run_only=False,
        response_finalized=True,
    )
    assert non_dry_run.status == "blocked"
    assert "non_dry_run_not_supported" in non_dry_run.blocked_reasons

    explicit_source = _admission(
        trigger_mode="explicit_memory_request",
        turn_index=None,
        visible_response_finalized=False,
    )
    assert explicit_source["admission_status"] == "admitted_dry_run"
    explicit = build_relaymem_slp_response_finalization_handoff(
        explicit_source,
        enabled=True,
        response_finalized=True,
    )
    assert explicit.status == "blocked"
    assert "trigger_not_supported_for_response_handoff" in explicit.blocked_reasons
    assert explicit.candidate_created is False

    held = build_relaymem_slp_response_finalization_handoff(
        _admission(persistence_policy_status="review_required"),
        enabled=True,
        response_finalized=True,
    )
    assert held.status == "held"
    assert held.candidate_created is False
    assert "source_admission_held" in held.blocked_reasons

    blocked = build_relaymem_slp_response_finalization_handoff(
        _admission(runtime_terminal_status="failed"),
        enabled=True,
        response_finalized=True,
    )
    assert blocked.status == "blocked"
    assert blocked.candidate_created is False
    assert "source_admission_blocked" in blocked.blocked_reasons

    skipped = build_relaymem_slp_response_finalization_handoff(
        _admission(source_count=0, source_lineage_artifact=None),
        enabled=True,
        response_finalized=True,
    )
    assert skipped.status == "skipped"
    assert skipped.candidate_created is False
    assert "source_admission_skipped" in skipped.blocked_reasons

    extra_field = deepcopy(_admission())
    extra_field["raw_response_text"] = "private"
    invalid_shape = build_relaymem_slp_response_finalization_handoff(
        extra_field,
        enabled=True,
        response_finalized=True,
    )
    assert invalid_shape.status == "invalid_input"
    assert "admission_result_shape_mismatch" in invalid_shape.blocked_reasons

    side_effect_source = deepcopy(_admission())
    side_effect_source["queue_io_performed"] = True
    invalid_side_effect = build_relaymem_slp_response_finalization_handoff(
        side_effect_source,
        enabled=True,
        response_finalized=True,
    )
    assert invalid_side_effect.status == "invalid_input"
    assert "source_queue_io_already_performed" in invalid_side_effect.blocked_reasons

    numeric_bool_source = deepcopy(_admission())
    numeric_bool_source["source_reference_valid"] = 1
    invalid_bool = build_relaymem_slp_response_finalization_handoff(
        numeric_bool_source,
        enabled=True,
        response_finalized=True,
    )
    assert invalid_bool.status == "invalid_input"
    assert "admission_source_reference_valid_invalid" in invalid_bool.blocked_reasons

    numeric_count_source = deepcopy(_admission())
    numeric_count_source["source_count"] = True
    invalid_count = build_relaymem_slp_response_finalization_handoff(
        numeric_count_source,
        enabled=True,
        response_finalized=True,
    )
    assert invalid_count.status == "invalid_input"
    assert "admission_source_count_invalid" in invalid_count.blocked_reasons

    nested_source_token = deepcopy(_admission())
    nested_source_token["trigger_mode"] = {"nested": {"private": "value"}}
    nested_source_token["projection"]["trigger_mode"] = {
        "nested": {"private": "value"}
    }
    nested_source_result = build_relaymem_slp_response_finalization_handoff(
        nested_source_token,
        enabled=True,
        response_finalized=True,
    )
    assert nested_source_result.status == "invalid_input"
    assert "admission_trigger_mode_invalid" in nested_source_result.blocked_reasons

    invalid_projection = deepcopy(_admission())
    invalid_projection["projection"] = "not-a-mapping"
    projection_result = build_relaymem_slp_response_finalization_handoff(
        invalid_projection,
        enabled=True,
        response_finalized=True,
    )
    assert projection_result.status == "invalid_input"
    assert "source_projection_invalid" in projection_result.blocked_reasons

    projection_extra = deepcopy(_admission())
    projection_extra["projection"]["raw_response_text"] = "private"
    projection_extra_result = build_relaymem_slp_response_finalization_handoff(
        projection_extra,
        enabled=True,
        response_finalized=True,
    )
    assert projection_extra_result.status == "invalid_input"
    assert "source_projection_shape_mismatch" in projection_extra_result.blocked_reasons

    projection_numeric = deepcopy(_admission())
    projection_numeric["projection"]["content_free"] = 1
    projection_numeric_result = build_relaymem_slp_response_finalization_handoff(
        projection_numeric,
        enabled=True,
        response_finalized=True,
    )
    assert projection_numeric_result.status == "invalid_input"
    assert "source_projection_content_free_invalid" in projection_numeric_result.blocked_reasons

    projection_numeric_count = deepcopy(_admission())
    projection_numeric_count["projection"]["source_count"] = True
    projection_count_result = build_relaymem_slp_response_finalization_handoff(
        projection_numeric_count,
        enabled=True,
        response_finalized=True,
    )
    assert projection_count_result.status == "invalid_input"
    assert "source_projection_source_count_invalid" in projection_count_result.blocked_reasons

    projection_nested_token = deepcopy(_admission())
    projection_nested_token["projection"]["trigger_mode"] = {
        "nested": {"private": "value"}
    }
    projection_nested_result = build_relaymem_slp_response_finalization_handoff(
        projection_nested_token,
        enabled=True,
        response_finalized=True,
    )
    assert projection_nested_result.status == "invalid_input"
    assert "source_projection_trigger_mode_invalid" in projection_nested_result.blocked_reasons

    projection_mismatch = deepcopy(_admission())
    projection_mismatch["projection"]["trigger_mode"] = "explicit_memory_request"
    projection_mismatch_result = build_relaymem_slp_response_finalization_handoff(
        projection_mismatch,
        enabled=True,
        response_finalized=True,
    )
    assert projection_mismatch_result.status == "invalid_input"
    assert "source_projection_mismatch:trigger_mode" in projection_mismatch_result.blocked_reasons

    correlation_mismatch = deepcopy(_admission())
    correlation_mismatch["projection"]["correlation"]["run_id_present"] = False
    correlation_mismatch_result = build_relaymem_slp_response_finalization_handoff(
        correlation_mismatch,
        enabled=True,
        response_finalized=True,
    )
    assert correlation_mismatch_result.status == "invalid_input"
    assert "source_projection_correlation_mismatch" in correlation_mismatch_result.blocked_reasons

    correlation_shape = deepcopy(_admission())
    correlation_shape["projection"]["correlation"]["raw_identifier"] = True
    correlation_shape_result = build_relaymem_slp_response_finalization_handoff(
        correlation_shape,
        enabled=True,
        response_finalized=True,
    )
    assert correlation_shape_result.status == "invalid_input"
    assert "source_projection_correlation_shape_mismatch" in correlation_shape_result.blocked_reasons

    correlation_nested = deepcopy(_admission())
    correlation_nested["projection"]["correlation"]["run_id_present"] = {
        "nested": {"private": "value"}
    }
    correlation_nested_result = build_relaymem_slp_response_finalization_handoff(
        correlation_nested,
        enabled=True,
        response_finalized=True,
    )
    assert correlation_nested_result.status == "invalid_input"
    assert "source_projection_correlation_invalid" in correlation_nested_result.blocked_reasons

    print("RelayMEM RelaySLP response-finalization handoff smoke passed")


if __name__ == "__main__":
    main()
