"""Fail-closed and leakage smoke for Phase 6-B1 dispatch preflight."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from relaylm.relaymem_slp_dispatch_preflight import (
    build_relaymem_slp_dispatch_preflight,
)
from relaylm.relaymem_slp_job_admission import (
    build_relaymem_slp_job_admission_preflight,
)
from relaylm.relaymem_slp_response_handoff import (
    RelayMEMSLPEnqueueCandidate,
    build_relaymem_slp_response_finalization_handoff,
)


def _lineage() -> dict[str, Any]:
    return {
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


def _handoff():
    admission = build_relaymem_slp_job_admission_preflight(
        enabled=True,
        dry_run_only=True,
        enqueue_enabled=False,
        trigger_mode="turn_end",
        processing_stage="primary_formation",
        run_id="run-1",
        turn_index=4,
        session_id="session-1",
        namespace="default",
        source_event_kind="turn",
        source_lineage_artifact=_lineage(),
        source_count=1,
        visible_response_finalized=True,
        runtime_terminal_status="completed",
        persistence_policy_status="allowed",
    )
    return build_relaymem_slp_response_finalization_handoff(
        admission,
        enabled=True,
        dry_run_only=True,
        response_finalized=True,
    )


def _assert_rejected(handoff: object, expected_reason: str) -> None:
    result = build_relaymem_slp_dispatch_preflight(handoff, enabled=True)
    assert result.status in {"invalid_input", "blocked"}, result
    assert result.durable_job_created is False
    assert expected_reason in result.blocked_reasons, result.blocked_reasons
    runtime = result.to_runtime_dict()
    assert runtime["queue_io_performed"] is False
    assert runtime["enqueue_attempted"] is False
    assert runtime["worker_invoked"] is False
    assert runtime["writes_memory"] is False
    assert runtime["mutates_soul"] is False
    assert runtime["changes_visible_response"] is False


def _with_candidate(handoff, **changes: Any):
    assert handoff.candidate is not None
    return replace(handoff, candidate=replace(handoff.candidate, **changes))


def main() -> None:
    handoff = _handoff()
    assert handoff.status == "dry_run_candidate"

    _assert_rejected(handoff.to_runtime_dict(), "exact_a2_handoff_result_required")
    _assert_rejected(None, "exact_a2_handoff_result_required")

    disabled_a2 = build_relaymem_slp_response_finalization_handoff(
        build_relaymem_slp_job_admission_preflight(
            enabled=True,
            dry_run_only=True,
            enqueue_enabled=False,
            trigger_mode="turn_end",
            processing_stage="primary_formation",
            run_id="run-1",
            turn_index=4,
            session_id="session-1",
            namespace="default",
            source_event_kind="turn",
            source_lineage_artifact=_lineage(),
            source_count=1,
            visible_response_finalized=True,
            runtime_terminal_status="completed",
            persistence_policy_status="allowed",
        ),
        enabled=False,
        response_finalized=True,
    )
    _assert_rejected(disabled_a2, "exact_a2_enqueue_candidate_required")

    assert handoff.source_projection is not None
    projection_count_mismatch = replace(
        handoff,
        source_projection=replace(handoff.source_projection, source_count=2),
    )
    _assert_rejected(
        projection_count_mismatch,
        "a2_candidate_source_projection_mismatch",
    )
    projection_session_mismatch = replace(
        handoff,
        source_projection=replace(
            handoff.source_projection,
            session_id_present=False,
        ),
    )
    _assert_rejected(
        projection_session_mismatch,
        "a2_candidate_source_projection_mismatch",
    )
    assert handoff.candidate is not None
    admission_mismatch = replace(
        handoff,
        source_admission_status="eligible_for_enqueue",
    )
    _assert_rejected(
        admission_mismatch,
        "a2_candidate_admission_status_mismatch",
    )

    _assert_rejected(
        _with_candidate(handoff, run_id=" run-1"),
        "a2_run_id_invalid",
    )
    _assert_rejected(
        _with_candidate(handoff, namespace="default\nsecret"),
        "a2_namespace_invalid",
    )
    _assert_rejected(
        _with_candidate(handoff, session_id=""),
        "a2_session_id_invalid",
    )
    _assert_rejected(
        _with_candidate(handoff, turn_index=True),
        "a2_turn_index_invalid",
    )
    _assert_rejected(
        _with_candidate(handoff, source_count=True),
        "a2_source_count_invalid",
    )
    _assert_rejected(
        _with_candidate(handoff, source_count=33),
        "a2_source_count_invalid",
    )
    _assert_rejected(
        _with_candidate(handoff, source_lineage_fingerprint="A" * 64),
        "a2_source_lineage_fingerprint_invalid",
    )
    _assert_rejected(
        _with_candidate(handoff, processing_stage="secondary_consolidation"),
        "a2_processing_stage_invalid",
    )
    _assert_rejected(
        _with_candidate(handoff, runtime_terminal_status="failed"),
        "a2_runtime_terminal_status_invalid",
    )
    _assert_rejected(
        _with_candidate(handoff, persistence_policy_status="review_required"),
        "a2_persistence_policy_status_invalid",
    )

    original = RelayMEMSLPEnqueueCandidate.to_runtime_dict

    def extra_field(self: RelayMEMSLPEnqueueCandidate) -> dict[str, object]:
        value = original(self)
        value["raw_response_text"] = "private"
        return value

    RelayMEMSLPEnqueueCandidate.to_runtime_dict = extra_field  # type: ignore[method-assign]
    try:
        _assert_rejected(_handoff(), "a2_candidate_shape_mismatch")
    finally:
        RelayMEMSLPEnqueueCandidate.to_runtime_dict = original  # type: ignore[method-assign]

    def prepopulated_dispatch(self: RelayMEMSLPEnqueueCandidate) -> dict[str, object]:
        value = original(self)
        value["dispatch_idempotency_key"] = "preexisting"
        return value

    RelayMEMSLPEnqueueCandidate.to_runtime_dict = prepopulated_dispatch  # type: ignore[method-assign]
    try:
        _assert_rejected(
            _handoff(),
            "a2_candidate_dispatch_idempotency_key_not_empty",
        )
    finally:
        RelayMEMSLPEnqueueCandidate.to_runtime_dict = original  # type: ignore[method-assign]

    def preexisting_side_effect(self: RelayMEMSLPEnqueueCandidate) -> dict[str, object]:
        value = original(self)
        value["queue_io_performed"] = True
        return value

    RelayMEMSLPEnqueueCandidate.to_runtime_dict = preexisting_side_effect  # type: ignore[method-assign]
    try:
        _assert_rejected(_handoff(), "a2_candidate_queue_io_performed_invalid")
    finally:
        RelayMEMSLPEnqueueCandidate.to_runtime_dict = original  # type: ignore[method-assign]

    ready = build_relaymem_slp_dispatch_preflight(handoff, enabled=True)
    assert ready.status == "dry_run_ready"
    assert ready.durable_job is not None
    projection_text = repr(ready.to_log_dict())
    for forbidden in (
        "run-1",
        "session-1",
        "default",
        "a" * 64,
        ready.durable_job.job_id,
        ready.durable_job.dispatch_idempotency_key,
    ):
        assert forbidden not in projection_text

    print("Phase 6-B1 dispatch preflight security smoke: ok")


if __name__ == "__main__":
    main()
