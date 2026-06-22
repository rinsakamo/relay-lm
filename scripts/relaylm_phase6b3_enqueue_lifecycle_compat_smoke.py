"""Regression smoke for B2 duplicate inspection after a B3 claim."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from relaylm.relaymem_slp_dispatch_preflight import build_relaymem_slp_dispatch_preflight
from relaylm.relaymem_slp_durable_enqueue import enqueue_relaymem_slp_durable_job
from relaylm.relaymem_slp_job_admission import build_relaymem_slp_job_admission_preflight
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)
from relaylm.relaymem_slp_response_handoff import (
    build_relaymem_slp_response_finalization_handoff,
)


def _preflight():
    lineage = {
        "schema_version": "relaymem.primary_source_lineage.v0",
        "content_free": True,
        "content_included": False,
        "raw_text_included": False,
        "source_event_kind": "turn",
        "namespace": "default",
        "valid": True,
        "lineage_fingerprint": "f" * 64,
        "lineage_shape": {
            "source_event_id_present": True,
            "run_id_present": True,
            "session_id_present": True,
            "turn_index_present": True,
        },
        "blocked_reasons": [],
    }
    admission = build_relaymem_slp_job_admission_preflight(
        enabled=True,
        dry_run_only=True,
        enqueue_enabled=False,
        trigger_mode="turn_end",
        processing_stage="primary_formation",
        run_id="run-lifecycle-compat",
        turn_index=7,
        session_id="session-lifecycle-compat",
        namespace="default",
        source_event_kind="turn",
        source_lineage_artifact=lineage,
        source_count=1,
        visible_response_finalized=True,
        runtime_terminal_status="completed",
        persistence_policy_status="allowed",
    )
    handoff = build_relaymem_slp_response_finalization_handoff(
        admission,
        enabled=True,
        dry_run_only=True,
        response_finalized=True,
    )
    return build_relaymem_slp_dispatch_preflight(
        handoff,
        enabled=True,
        dry_run_only=True,
    )


def main() -> None:
    preflight = _preflight()
    assert preflight.status == "dry_run_ready"
    assert preflight.durable_job is not None

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        enqueued = enqueue_relaymem_slp_durable_job(
            preflight,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert enqueued.status == "enqueued_new"
        record_path = next(root.glob("slp-dispatch-v0-*.json"))
        queued = json.loads(record_path.read_text(encoding="utf-8"))

        claimed = transition_relaymem_slp_queue_state(
            RelayMEMSLPQueueTransitionRequest(
                transition_kind="claim",
                job_id=queued["job_id"],
                dispatch_idempotency_key=queued["dispatch_idempotency_key"],
                expected_record_revision=queued["record_revision"],
                expected_state=queued["state"],
                claim_owner="worker-lifecycle-compat",
                claim_generation=queued["claim_generation"],
                lease_token="",
                lease_duration_seconds=30,
                retry_class="unclassified",
                retry_not_before=None,
                failure_class="none",
                terminal_state="",
                terminal_reason_id="",
            ),
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert claimed.status == "applied"
        claimed_bytes = record_path.read_bytes()
        claimed_record = json.loads(claimed_bytes.decode("utf-8"))
        assert claimed_record["state"] == "claimed"
        assert claimed_record["record_revision"] == 1
        assert claimed_record["attempt_count"] == 1
        assert claimed_record["claim_generation"] == 1

        duplicate = enqueue_relaymem_slp_durable_job(
            preflight,
            queue_root=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert duplicate.status == "duplicate_existing"
        assert duplicate.outcome == "duplicate_existing"
        assert duplicate.duplicate_detected is True
        assert duplicate.enqueue_applied is False
        assert duplicate.durable_record == claimed_record
        assert record_path.read_bytes() == claimed_bytes

    print("Phase 6-B3 enqueue lifecycle compatibility smoke: ok")


if __name__ == "__main__":
    main()
