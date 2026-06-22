"""Functional smoke coverage for Phase 6-B3 queue state helpers."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import relaylm.relaymem_slp_queue_state as queue_state
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    build_relaymem_slp_queue_state_node_result,
    transition_relaymem_slp_queue_state,
)


def _initial_record(*, run_id: str = "run-1", lineage: str = "a" * 64) -> dict[str, object]:
    created = "2026-06-22T00:00:00.000000Z"
    record: dict[str, object] = {
        "schema_version": "relaymem.slp_durable_job.v0",
        "job_id": "",
        "dispatch_idempotency_key": "",
        "dispatch_key_version": "relaymem.slp_dispatch_key.v0",
        "candidate_schema_version": "relaymem.slp_enqueue_candidate.v0",
        "candidate_kind": "relayslp_deferred_job",
        "trigger_mode": "turn_end",
        "processing_stage": "primary_formation",
        "source_event_kind": "turn",
        "run_id": run_id,
        "turn_index": 4,
        "session_id": "session-1",
        "namespace": "default",
        "source_count": 1,
        "source_lineage_fingerprint": lineage,
        "source_admission_status": "admitted_dry_run",
        "runtime_terminal_status": "completed",
        "persistence_policy_status": "allowed",
        "state": "queued",
        "record_revision": 0,
        "created_at": created,
        "updated_at": created,
        "attempt_count": 0,
        "claim_generation": 0,
        "claim_owner": "",
        "lease_token": "",
        "lease_acquired_at": None,
        "lease_expires_at": None,
        "retry_class": "unclassified",
        "retry_not_before": None,
        "failure_class": "none",
        "terminal_reason_id": "",
    }
    dispatch = queue_state._derive_dispatch_key(record)
    record["dispatch_idempotency_key"] = dispatch
    record["job_id"] = queue_state._derive_job_id(dispatch)
    assert not queue_state._validate_record_mapping(record)
    return record


def _write(root: Path, record: dict[str, object]) -> Path:
    path = root / queue_state._record_filename(str(record["dispatch_idempotency_key"]))
    path.write_bytes(queue_state._canonical_json_bytes(record))
    return path


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _request(record: dict[str, object], kind: str, **overrides: Any) -> RelayMEMSLPQueueTransitionRequest:
    values: dict[str, Any] = {
        "transition_kind": kind,
        "job_id": record["job_id"],
        "dispatch_idempotency_key": record["dispatch_idempotency_key"],
        "expected_record_revision": record["record_revision"],
        "expected_state": record["state"],
        "claim_owner": "",
        "claim_generation": record["claim_generation"],
        "lease_token": "",
        "lease_duration_seconds": 0,
        "retry_class": "unclassified",
        "retry_not_before": None,
        "failure_class": "none",
        "terminal_state": "",
        "terminal_reason_id": "",
    }
    values.update(overrides)
    return RelayMEMSLPQueueTransitionRequest(**values)


def _apply(root: Path, request: RelayMEMSLPQueueTransitionRequest):
    return transition_relaymem_slp_queue_state(
        request,
        queue_root=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
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
    base_now = datetime(2026, 6, 22, 1, 0, tzinfo=timezone.utc)
    original_now = queue_state._now_utc
    queue_state._now_utc = lambda: base_now
    try:
        record = _initial_record()
        disabled = transition_relaymem_slp_queue_state(
            _request(record, "claim", claim_owner="worker-a", lease_duration_seconds=30),
            queue_root=None,
        )
        assert disabled.status == "disabled"
        assert disabled.queue_io_performed is False

        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, record)
            original_bytes = path.read_bytes()
            claim_request = _request(record, "claim", claim_owner="worker-a", lease_duration_seconds=30)
            dry_run = transition_relaymem_slp_queue_state(
                claim_request,
                queue_root=str(root),
                enabled=True,
            )
            assert dry_run.status == "dry_run_ready"
            assert dry_run.proposed_state == "claimed"
            assert dry_run.transition_applied is False
            assert path.read_bytes() == original_bytes

            claim = _apply(root, claim_request)
            assert claim.status == "applied"
            assert claim.transition_applied is True
            claimed = _read(path)
            assert claimed["state"] == "claimed"
            assert claimed["record_revision"] == 1
            assert claimed["attempt_count"] == 1
            assert claimed["claim_generation"] == 1
            assert claimed["claim_owner"] == "worker-a"
            assert claimed["lease_token"]

            queue_state._now_utc = lambda: base_now + timedelta(seconds=5)
            renew = _apply(root, _request(
                claimed,
                "renew_lease",
                claim_owner="worker-a",
                lease_token=claimed["lease_token"],
                lease_duration_seconds=30,
            ))
            assert renew.status == "applied"
            renewed = _read(path)
            assert renewed["record_revision"] == 2
            assert renewed["attempt_count"] == 1
            assert renewed["claim_generation"] == 1
            assert renewed["lease_token"] == claimed["lease_token"]
            assert renewed["claim_owner"] == claimed["claim_owner"]
            assert renewed["lease_acquired_at"] == claimed["lease_acquired_at"]
            assert renewed["lease_expires_at"] == "2026-06-22T01:00:35.000000Z"
            assert renewed["lease_expires_at"] != "2026-06-22T01:01:00.000000Z"

            queue_state._now_utc = lambda: base_now + timedelta(seconds=10)
            release = _apply(root, _request(
                renewed,
                "retry_release",
                claim_owner="worker-a",
                lease_token=renewed["lease_token"],
                retry_class="transient_backend",
                retry_not_before="2026-06-22T01:01:00.000000Z",
                failure_class="backend_unavailable",
            ))
            assert release.status == "applied"
            released = _read(path)
            assert released["state"] == "queued"
            assert released["record_revision"] == 3
            assert released["attempt_count"] == 1
            assert released["claim_generation"] == 1
            assert released["claim_owner"] == ""
            assert released["lease_token"] == ""

            not_ready = _apply(root, _request(
                released,
                "claim",
                claim_owner="worker-b",
                lease_duration_seconds=30,
            ))
            assert not_ready.status == "not_ready"
            assert _read(path) == released

            queue_state._now_utc = lambda: base_now + timedelta(minutes=1)
            reclaim = _apply(root, _request(
                released,
                "claim",
                claim_owner="worker-b",
                lease_duration_seconds=30,
            ))
            assert reclaim.status == "applied"
            reclaimed = _read(path)
            assert reclaimed["record_revision"] == 4
            assert reclaimed["attempt_count"] == 2
            assert reclaimed["claim_generation"] == 2

            queue_state._now_utc = lambda: base_now + timedelta(minutes=1, seconds=5)
            terminal = _apply(root, _request(
                reclaimed,
                "commit_terminal",
                claim_owner="worker-b",
                lease_token=reclaimed["lease_token"],
                terminal_state="succeeded",
                terminal_reason_id="worker_completed",
            ))
            assert terminal.status == "applied"
            succeeded = _read(path)
            assert succeeded["state"] == "succeeded"
            assert succeeded["record_revision"] == 5
            assert succeeded["claim_owner"] == ""
            assert succeeded["lease_token"] == ""
            assert succeeded["terminal_reason_id"] == "worker_completed"

            immutable = _apply(root, _request(
                succeeded,
                "commit_terminal",
                terminal_state="cancelled",
                terminal_reason_id="cancelled_again",
            ))
            assert immutable.status == "blocked"
            assert "terminal_state_immutable" in immutable.blocked_reasons
            assert _read(path) == succeeded

            projection = terminal.to_log_dict()
            node = build_relaymem_slp_queue_state_node_result(terminal)
            assert projection["transition_kind"] == "commit_terminal"
            assert projection["queue_state"] == "succeeded"
            assert projection["terminal"] is True
            assert node.node_name == "relaymem_slp_queue_state"
            private_values = (
                record["job_id"], record["dispatch_idempotency_key"], "worker-b",
                reclaimed["lease_token"], str(path), succeeded["updated_at"], "run-1", "session-1",
            )
            for private in private_values:
                assert _contains(projection, private) is False
                assert _contains(node.to_log_dict(), private) is False

        stale_record = _initial_record(run_id="run-stale", lineage="b" * 64)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, stale_record)
            queue_state._now_utc = lambda: base_now
            first_claim = _apply(root, _request(
                stale_record, "claim", claim_owner="worker-stale", lease_duration_seconds=30,
            ))
            assert first_claim.status == "applied"
            claimed = _read(path)
            expiry = datetime.fromisoformat(str(claimed["lease_expires_at"])[:-1] + "+00:00")

            queue_state._now_utc = lambda: expiry - timedelta(microseconds=1)
            before = _apply(root, _request(
                claimed, "stale_recovery", claim_owner="different-owner", lease_token=claimed["lease_token"],
            ))
            assert before.status == "not_ready"

            queue_state._now_utc = lambda: expiry
            at_expiry = _apply(root, _request(
                claimed, "stale_recovery", claim_owner="different-owner", lease_token=claimed["lease_token"],
            ))
            assert at_expiry.status == "applied"
            recovered = _read(path)
            assert recovered["state"] == "queued"
            assert recovered["record_revision"] == 2
            assert recovered["attempt_count"] == 1
            assert recovered["claim_generation"] == 1
            assert recovered["retry_class"] == "stale_lease_recovery"
            assert recovered["failure_class"] == "stale_lease_expired"

            queue_state._now_utc = lambda: expiry + timedelta(seconds=1)
            second_claim = _apply(root, _request(
                recovered, "claim", claim_owner="worker-new", lease_duration_seconds=30,
            ))
            assert second_claim.status == "applied"
            reclaimed = _read(path)
            assert reclaimed["record_revision"] == 3
            assert reclaimed["attempt_count"] == 2
            assert reclaimed["claim_generation"] == 2

        for target, failure_class, suffix in (
            ("failed", "worker_failure", "d"),
            ("cancelled", "none", "e"),
        ):
            terminal_record = _initial_record(
                run_id=f"run-{target}", lineage=suffix * 64,
            )
            with TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                path = _write(root, terminal_record)
                queue_state._now_utc = lambda: base_now
                claimed_result = _apply(root, _request(
                    terminal_record, "claim", claim_owner="worker-terminal", lease_duration_seconds=30,
                ))
                assert claimed_result.status == "applied"
                claimed_record = _read(path)
                queue_state._now_utc = lambda: base_now + timedelta(seconds=1)
                terminal_result = _apply(root, _request(
                    claimed_record,
                    "commit_terminal",
                    claim_owner="worker-terminal",
                    lease_token=claimed_record["lease_token"],
                    failure_class=failure_class,
                    terminal_state=target,
                    terminal_reason_id=f"worker_{target}",
                ))
                assert terminal_result.status == "applied"
                persisted_terminal = _read(path)
                assert persisted_terminal["state"] == target
                assert persisted_terminal["failure_class"] == failure_class

        queued = _initial_record(run_id="run-cancel", lineage="c" * 64)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, queued)
            queue_state._now_utc = lambda: base_now
            cancelled = _apply(root, _request(
                queued, "commit_terminal", terminal_state="cancelled", terminal_reason_id="operator_cancelled",
            ))
            assert cancelled.status == "applied"
            assert _read(path)["state"] == "cancelled"

        print("Phase 6-B3 queue state smoke: ok")
    finally:
        queue_state._now_utc = original_now


if __name__ == "__main__":
    main()
