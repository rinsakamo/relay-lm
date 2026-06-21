"""Regression smoke for strict Phase 6-A2 status and source projection."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from relaylm.relaymem_slp_job_admission import (
    build_relaymem_slp_job_admission_preflight,
)
from relaylm.relaymem_slp_response_handoff import (
    RelayMEMSLPResponseHandoffResult,
    build_relaymem_slp_response_finalization_handoff,
)


def _admission(**overrides: Any) -> dict[str, Any]:
    lineage = {
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
    values: dict[str, Any] = {
        "enabled": True,
        "dry_run_only": True,
        "enqueue_enabled": False,
        "trigger_mode": "turn_end",
        "processing_stage": "primary_formation",
        "run_id": "run-1",
        "turn_index": 1,
        "session_id": "session-1",
        "namespace": "default",
        "source_event_kind": "turn",
        "source_lineage_artifact": lineage,
        "source_count": 1,
        "visible_response_finalized": True,
        "runtime_terminal_status": "completed",
        "persistence_policy_status": "allowed",
    }
    values.update(overrides)
    return build_relaymem_slp_job_admission_preflight(**values)


def _handoff(
    source: dict[str, Any],
    *,
    dry_run_only: bool = True,
    response_finalized: bool = True,
) -> RelayMEMSLPResponseHandoffResult:
    return build_relaymem_slp_response_finalization_handoff(
        source,
        enabled=True,
        dry_run_only=dry_run_only,
        response_finalized=response_finalized,
    )


def _assert_source_projection(result: RelayMEMSLPResponseHandoffResult) -> None:
    assert result.candidate_created is False
    log = result.to_log_dict()
    assert log["trigger_mode"] == "turn_end"
    assert log["processing_stage"] == "primary_formation"
    assert log["source_event_kind"] == "turn"
    assert log["source_count"] == 1
    assert log["correlation"] == {
        "run_id_present": True,
        "turn_index_present": True,
        "session_id_present": True,
        "namespace_present": True,
    }
    runtime = result.to_runtime_dict()
    assert runtime["source_projection"] == {
        "trigger_mode": "turn_end",
        "processing_stage": "primary_formation",
        "source_event_kind": "turn",
        "source_count": 1,
        "correlation": {
            "run_id_present": True,
            "turn_index_present": True,
            "session_id_present": True,
            "namespace_present": True,
        },
    }


def main() -> None:
    malformed_values: tuple[Any, ...] = (
        {"nested": {"private": "value"}},
        ["admitted_dry_run"],
        1,
        True,
        None,
    )

    for malformed in malformed_values:
        private_source = deepcopy(_admission())
        private_source["admission_status"] = malformed
        result = _handoff(private_source)
        assert result.status == "invalid_input"
        assert "admission_status_invalid" in result.blocked_reasons

        projection_source = deepcopy(_admission())
        projection_source["projection"]["admission_status"] = malformed
        result = _handoff(projection_source)
        assert result.status == "invalid_input"
        assert "source_projection_admission_status_invalid" in result.blocked_reasons

    unknown_private = deepcopy(_admission())
    unknown_private["admission_status"] = "unknown"
    result = _handoff(unknown_private)
    assert result.status == "invalid_input"
    assert "admission_status_invalid" in result.blocked_reasons

    unknown_projection = deepcopy(_admission())
    unknown_projection["projection"]["admission_status"] = "unknown"
    result = _handoff(unknown_projection)
    assert result.status == "invalid_input"
    assert "source_projection_admission_status_invalid" in result.blocked_reasons

    held = _handoff(_admission(persistence_policy_status="review_required"))
    assert held.status == "held"
    assert held.response_finalized is True
    _assert_source_projection(held)

    non_dry_run = _handoff(_admission(), dry_run_only=False)
    assert non_dry_run.status == "blocked"
    assert "non_dry_run_not_supported" in non_dry_run.blocked_reasons
    assert non_dry_run.response_finalized is True
    _assert_source_projection(non_dry_run)

    failed = _handoff(_admission(runtime_terminal_status="failed"))
    assert failed.status == "blocked"
    assert "source_admission_blocked" in failed.blocked_reasons
    _assert_source_projection(failed)

    not_finalized = _handoff(_admission(), response_finalized=False)
    assert not_finalized.status == "blocked"
    assert not_finalized.response_finalized is False
    assert "response_not_finalized" in not_finalized.blocked_reasons
    _assert_source_projection(not_finalized)

    skipped = _handoff(_admission(source_count=0, source_lineage_artifact=None))
    assert skipped.status == "skipped"
    assert skipped.candidate_created is False
    skipped_log = skipped.to_log_dict()
    assert skipped_log["trigger_mode"] == "turn_end"
    assert skipped_log["processing_stage"] == "primary_formation"
    assert skipped_log["source_event_kind"] == "turn"
    assert skipped_log["source_count"] == 0
    assert skipped_log["correlation"] == {
        "run_id_present": True,
        "turn_index_present": True,
        "session_id_present": True,
        "namespace_present": True,
    }

    print("RelayMEM RelaySLP response-handoff status smoke passed")


if __name__ == "__main__":
    main()
