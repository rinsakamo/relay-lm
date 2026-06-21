"""Functional smoke coverage for Phase 6-B2 durable RelaySLP enqueue."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from relaylm.relaymem_slp_dispatch_preflight import build_relaymem_slp_dispatch_preflight
from relaylm.relaymem_slp_durable_enqueue import (
    build_relaymem_slp_durable_enqueue_node_result,
    enqueue_relaymem_slp_durable_job,
)
from relaylm.relaymem_slp_job_admission import build_relaymem_slp_job_admission_preflight
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
    admission = build_relaymem_slp_job_admission_preflight(**values)
    return build_relaymem_slp_response_finalization_handoff(
        admission,
        enabled=True,
        dry_run_only=True,
        response_finalized=True,
    )


def _preflight(**overrides: Any):
    return build_relaymem_slp_dispatch_preflight(
        _handoff(**overrides),
        enabled=True,
        dry_run_only=True,
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
    ready = _preflight()
    assert ready.status == "dry_run_ready"
    assert ready.durable_job is not None

    disabled = enqueue_relaymem_slp_durable_job(
        ready,
        queue_root=None,
    )
    assert disabled.status == "disabled"
    assert disabled.queue_io_performed is False

    invalid_gate = enqueue_relaymem_slp_durable_job(
        ready,
        queue_root=None,
        enabled=1,
    )
    assert invalid_gate.status == "invalid_input"
    assert "enabled_invalid" in invalid_gate.blocked_reasons

    lookalike = enqueue_relaymem_slp_durable_job(
        ready.to_runtime_dict(),
        queue_root=None,
        enabled=True,
    )
    assert lookalike.status == "invalid_input"
    assert "exact_b1_preflight_result_required" in lookalike.blocked_reasons

    with TemporaryDirectory() as directory:
        queue_root = Path(directory).resolve()
        dry_run = enqueue_relaymem_slp_durable_job(
            ready,
            queue_root=str(queue_root),
            enabled=True,
        )
        assert dry_run.status == "dry_run_ready"
        assert dry_run.outcome is None
        assert dry_run.queue_io_performed is True
        assert dry_run.enqueue_attempted is False
        assert dry_run.enqueue_applied is False
        assert list(queue_root.iterdir()) == []

        applied = enqueue_relaymem_slp_durable_job(
            ready,
            queue_root=str(queue_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert applied.status == "enqueued_new"
        assert applied.outcome == "enqueued_new"
        assert applied.enqueue_attempted is True
        assert applied.enqueue_applied is True
        assert applied.duplicate_detected is False
        assert applied.durability_confirmed is True
        assert applied.durable_record is not None
        assert applied.durable_record["created_at"] == applied.durable_record["updated_at"]
        assert str(applied.durable_record["created_at"]).endswith("Z")
        assert applied.durable_record["state"] == "queued"
        assert applied.durable_record["record_revision"] == 0

        records = list(queue_root.glob("slp-dispatch-v0-*.json"))
        assert len(records) == 1
        record_path = records[0]
        original_bytes = record_path.read_bytes()
        persisted = json.loads(original_bytes.decode("utf-8"))
        assert persisted == applied.durable_record
        assert original_bytes == json.dumps(
            persisted,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

        duplicate = enqueue_relaymem_slp_durable_job(
            ready,
            queue_root=str(queue_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert duplicate.status == "duplicate_existing"
        assert duplicate.outcome == "duplicate_existing"
        assert duplicate.enqueue_attempted is True
        assert duplicate.enqueue_applied is False
        assert duplicate.duplicate_detected is True
        assert record_path.read_bytes() == original_bytes

        source = _handoff()
        candidate = source.candidate
        assert candidate is not None
        operational_candidate = replace(
            candidate,
            source_admission_status="eligible_for_enqueue",
            runtime_terminal_status="succeeded",
            persistence_policy_status="free_to_update",
        )
        operational_handoff = replace(
            source,
            source_admission_status="eligible_for_enqueue",
            candidate=operational_candidate,
        )
        operational = build_relaymem_slp_dispatch_preflight(
            operational_handoff,
            enabled=True,
            dry_run_only=True,
        )
        assert operational.durable_job is not None
        assert (
            operational.durable_job.dispatch_idempotency_key
            == ready.durable_job.dispatch_idempotency_key
        )
        operational_duplicate = enqueue_relaymem_slp_durable_job(
            operational,
            queue_root=str(queue_root),
            enabled=True,
        )
        assert operational_duplicate.status == "duplicate_existing"
        assert record_path.read_bytes() == original_bytes

        other = _preflight(processing_stage="primary_write_preflight")
        other_applied = enqueue_relaymem_slp_durable_job(
            other,
            queue_root=str(queue_root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert other_applied.status == "enqueued_new"
        assert len(list(queue_root.glob("slp-dispatch-v0-*.json"))) == 2

        projection = applied.to_log_dict()
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
        assert projection["enqueue_applied"] is True
        assert projection["claim_active"] is False
        assert projection["lease_present"] is False
        assert projection["terminal"] is False

        node = build_relaymem_slp_durable_enqueue_node_result(applied)
        assert node.node_name == "relaymem_slp_durable_enqueue"
        assert node.decision == "enqueued_new"
        assert node.artifacts[0]["record_omitted"] is True
        assert node.artifacts[0]["dispatch_idempotency_key_included"] is False
        assert node.artifacts[0]["job_id_included"] is False
        assert node.artifacts[0]["queue_path_included"] is False
        assert node.artifacts[0]["timestamps_included"] is False

        private_values = (
            "run-1",
            "session-1",
            "default",
            "a" * 64,
            ready.durable_job.job_id,
            ready.durable_job.dispatch_idempotency_key,
            str(record_path),
            applied.durable_record["created_at"],
        )
        for private_value in private_values:
            assert _contains(projection, private_value) is False
            assert _contains(node.to_log_dict(), private_value) is False

    missing_root = enqueue_relaymem_slp_durable_job(
        ready,
        queue_root=str((Path(directory) / "missing").resolve()),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    assert missing_root.status == "write_failed"
    assert missing_root.outcome == "write_failed"
    assert "queue_root_missing" in missing_root.blocked_reasons

    print("Phase 6-B2 durable enqueue smoke: ok")


if __name__ == "__main__":
    main()
