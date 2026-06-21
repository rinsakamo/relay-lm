"""Smoke coverage for Phase 6-B1 RelaySLP dispatch preflight."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from relaylm.relaymem_slp_dispatch_preflight import (
    build_relaymem_slp_dispatch_preflight,
    build_relaymem_slp_dispatch_preflight_node_result,
)
from relaylm.relaymem_slp_job_admission import (
    build_relaymem_slp_job_admission_preflight,
)
from relaylm.relaymem_slp_response_handoff import (
    build_relaymem_slp_response_finalization_handoff,
)


def _lineage(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
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
    value.update(overrides)
    return value


def _handoff(**overrides: Any):
    admission_values: dict[str, Any] = {
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
    admission_values.update(overrides)
    admission = build_relaymem_slp_job_admission_preflight(**admission_values)
    return build_relaymem_slp_response_finalization_handoff(
        admission,
        enabled=True,
        dry_run_only=True,
        response_finalized=True,
    )


def _contains(value: Any, target: Any) -> bool:
    if value == target:
        return True
    if isinstance(value, dict):
        return any(_contains(item, target) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains(item, target) for item in value)
    return False


def main() -> None:
    handoff = _handoff()
    assert handoff.status == "dry_run_candidate"

    disabled = build_relaymem_slp_dispatch_preflight(handoff)
    assert disabled.status == "disabled"
    assert disabled.durable_job_created is False
    assert disabled.to_runtime_dict()["queue_io_performed"] is False

    invalid_enabled = build_relaymem_slp_dispatch_preflight(handoff, enabled=1)
    assert invalid_enabled.status == "invalid_input"
    assert "enabled_invalid" in invalid_enabled.blocked_reasons

    invalid_dry_run = build_relaymem_slp_dispatch_preflight(
        handoff,
        enabled=True,
        dry_run_only=1,
    )
    assert invalid_dry_run.status == "invalid_input"
    assert "dry_run_only_invalid" in invalid_dry_run.blocked_reasons

    non_dry_run = build_relaymem_slp_dispatch_preflight(
        handoff,
        enabled=True,
        dry_run_only=False,
    )
    assert non_dry_run.status == "blocked"
    assert "non_dry_run_not_supported" in non_dry_run.blocked_reasons

    ready = build_relaymem_slp_dispatch_preflight(handoff, enabled=True)
    assert ready.status == "dry_run_ready"
    assert ready.source_candidate_valid is True
    assert ready.response_finalized is True
    assert ready.durable_job_created is True
    assert ready.durable_job_count == 1
    assert ready.durable_job is not None

    runtime = ready.to_runtime_dict()
    job = runtime["durable_job"]
    assert isinstance(job, dict)
    assert job["schema_version"] == "relaymem.slp_durable_job.v0"
    assert job["dispatch_key_version"] == "relaymem.slp_dispatch_key.v0"
    assert job["candidate_schema_version"] == "relaymem.slp_enqueue_candidate.v0"
    assert job["candidate_kind"] == "relayslp_deferred_job"
    assert job["job_id"].startswith("slp-job-v0:")
    assert job["dispatch_idempotency_key"].startswith("slp-dispatch-v0:")
    assert job["job_id"] != job["dispatch_idempotency_key"]
    assert job["state"] == "queued"
    assert job["record_revision"] == 0
    assert job["created_at"] is None
    assert job["updated_at"] is None
    assert job["attempt_count"] == 0
    assert job["claim_generation"] == 0
    assert job["claim_owner"] == ""
    assert job["lease_token"] == ""
    assert job["lease_acquired_at"] is None
    assert job["lease_expires_at"] is None
    assert job["retry_class"] == "unclassified"
    assert job["retry_not_before"] is None
    assert job["failure_class"] == "none"
    assert job["terminal_reason_id"] == ""
    assert runtime["queue_io_performed"] is False
    assert runtime["enqueue_attempted"] is False
    assert runtime["enqueue_applied"] is False
    assert runtime["duplicate_detected"] is False
    assert runtime["worker_invoked"] is False
    assert runtime["writes_memory"] is False
    assert runtime["mutates_soul"] is False
    assert runtime["changes_visible_response"] is False

    repeated = build_relaymem_slp_dispatch_preflight(_handoff(), enabled=True)
    assert repeated.durable_job is not None
    assert repeated.durable_job.to_runtime_dict() == job

    candidate = handoff.candidate
    assert candidate is not None
    operational_candidate = replace(
        candidate,
        source_admission_status="eligible_for_enqueue",
        runtime_terminal_status="succeeded",
        persistence_policy_status="free_to_update",
    )
    operational_handoff = replace(
        handoff,
        source_admission_status="eligible_for_enqueue",
        candidate=operational_candidate,
    )
    operational = build_relaymem_slp_dispatch_preflight(
        operational_handoff,
        enabled=True,
    )
    assert operational.status == "dry_run_ready"
    assert operational.durable_job is not None
    assert (
        operational.durable_job.dispatch_idempotency_key
        == ready.durable_job.dispatch_idempotency_key
    )
    assert operational.durable_job.job_id == ready.durable_job.job_id

    no_session = build_relaymem_slp_dispatch_preflight(
        _handoff(session_id=None),
        enabled=True,
    )
    assert no_session.durable_job is not None
    assert (
        no_session.durable_job.dispatch_idempotency_key
        != ready.durable_job.dispatch_idempotency_key
    )

    other_stage = build_relaymem_slp_dispatch_preflight(
        _handoff(processing_stage="primary_write_preflight"),
        enabled=True,
    )
    assert other_stage.durable_job is not None
    assert (
        other_stage.durable_job.dispatch_idempotency_key
        != ready.durable_job.dispatch_idempotency_key
    )

    projection = ready.to_log_dict()
    assert set(projection) == {
        "schema_version",
        "status",
        "state",
        "trigger_mode",
        "processing_stage",
        "source_event_kind",
        "source_count",
        "attempt_count",
        "retry_class",
        "response_finalized",
        "enqueue_attempted",
        "enqueue_applied",
        "duplicate_detected",
        "claim_active",
        "lease_present",
        "terminal",
        "failure_class",
        "blocked_reason_ids",
    }
    assert projection["schema_version"] == "relaymem.slp_queue_status_projection.v0"
    assert projection["state"] == "queued"
    assert projection["enqueue_attempted"] is False
    assert projection["claim_active"] is False
    assert projection["lease_present"] is False
    assert projection["terminal"] is False
    for private_value in (
        "run-1",
        "session-1",
        "default",
        "a" * 64,
        job["job_id"],
        job["dispatch_idempotency_key"],
    ):
        assert _contains(projection, private_value) is False

    node = build_relaymem_slp_dispatch_preflight_node_result(ready)
    assert node.node_name == "relaymem_slp_dispatch_preflight"
    assert node.status == "diagnostic_only"
    assert node.decision == "dry_run_ready"
    assert node.artifacts[0]["candidate_omitted"] is True
    assert node.artifacts[0]["dispatch_idempotency_key_included"] is False
    assert node.artifacts[0]["job_id_included"] is False
    assert node.artifacts[0]["queue_io_performed"] is False
    for private_value in (
        "run-1",
        "session-1",
        "default",
        "a" * 64,
        job["job_id"],
        job["dispatch_idempotency_key"],
    ):
        assert _contains(node.to_log_dict(), private_value) is False

    print("Phase 6-B1 dispatch preflight smoke: ok")


if __name__ == "__main__":
    main()
