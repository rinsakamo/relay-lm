"""Security and fail-closed smoke for Phase 6-B3 queue state helpers."""
from __future__ import annotations

import fcntl
import json
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import relaylm.relaymem_slp_queue_state as queue_state
import relaylm.relaymem_slp_queue_storage as queue_storage
from relaylm.relaymem_slp_queue_state import (
    RelayMEMSLPQueueTransitionRequest,
    transition_relaymem_slp_queue_state,
)


def _record(*, run_id: str = "secure-run", lineage: str = "d" * 64) -> dict[str, object]:
    created = "2026-06-22T00:00:00.000000Z"
    value: dict[str, object] = {
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
        "turn_index": 9,
        "session_id": "secure-session",
        "namespace": "private-namespace",
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
    key = queue_state._derive_dispatch_key(value)
    value["dispatch_idempotency_key"] = key
    value["job_id"] = queue_state._derive_job_id(key)
    return value


def _filename(record: dict[str, object]) -> str:
    return queue_state._record_filename(str(record["dispatch_idempotency_key"]))


def _write(root: Path, record: dict[str, object]) -> Path:
    path = root / _filename(record)
    path.write_bytes(queue_state._canonical_json_bytes(record))
    return path


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _request(record: dict[str, object], kind: str = "claim", **overrides: Any):
    values: dict[str, Any] = {
        "transition_kind": kind,
        "job_id": record["job_id"],
        "dispatch_idempotency_key": record["dispatch_idempotency_key"],
        "expected_record_revision": record["record_revision"],
        "expected_state": record["state"],
        "claim_owner": "worker-secure" if kind == "claim" else "",
        "claim_generation": record["claim_generation"],
        "lease_token": "",
        "lease_duration_seconds": 30 if kind == "claim" else 0,
        "retry_class": "unclassified",
        "retry_not_before": None,
        "failure_class": "none",
        "terminal_state": "",
        "terminal_reason_id": "",
    }
    values.update(overrides)
    return RelayMEMSLPQueueTransitionRequest(**values)


def _call(root: Path, request: object, *, apply: bool = True):
    return transition_relaymem_slp_queue_state(
        request,
        queue_root=str(root),
        enabled=True,
        dry_run_only=not apply,
        apply_enabled=apply,
    )


def _claim(root: Path, record: dict[str, object]):
    result = _call(root, _request(record))
    assert result.status == "applied"
    return _read(root / _filename(record))


def main() -> None:
    base_now = datetime(2026, 6, 22, 2, 0, tzinfo=timezone.utc)
    original_now = queue_state._now_utc
    original_reopen = queue_storage.reopen_and_compare
    queue_state._now_utc = lambda: base_now
    try:
        record = _record()
        lookalike = transition_relaymem_slp_queue_state(
            _request(record).to_runtime_dict(), queue_root=None, enabled=True,
        )
        assert lookalike.status == "invalid_input"
        assert "exact_transition_request_required" in lookalike.blocked_reasons
        invalid_bool = transition_relaymem_slp_queue_state(
            _request(record), queue_root=None, enabled=1,
        )
        assert invalid_bool.status == "invalid_input"
        assert "enabled_invalid" in invalid_bool.blocked_reasons
        invalid_revision = _request(record, expected_record_revision=True)
        result = transition_relaymem_slp_queue_state(invalid_revision, queue_root=None, enabled=True)
        assert result.status == "invalid_input"
        assert "expected_record_revision_invalid" in result.blocked_reasons
        invalid_dead_letter = _request(
            record, "commit_terminal", claim_owner="", lease_duration_seconds=0,
            terminal_state="dead_letter", terminal_reason_id="not_allowed",
        )
        result = transition_relaymem_slp_queue_state(invalid_dead_letter, queue_root=None, enabled=True)
        assert result.status == "invalid_input"
        assert "terminal_state_invalid" in result.blocked_reasons

        other = _record(run_id="other-run", lineage="e" * 64)
        mixed = replace(_request(record), job_id=other["job_id"])
        result = transition_relaymem_slp_queue_state(mixed, queue_root=None, enabled=True)
        assert result.status == "invalid_input"
        assert "job_dispatch_identity_mismatch" in result.blocked_reasons

        relative = transition_relaymem_slp_queue_state(
            _request(record), queue_root="relative/queue", enabled=True,
        )
        assert relative.status == "write_failed"
        assert "queue_root_must_be_absolute" in relative.blocked_reasons
        with TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            not_directory = parent / "not-directory"
            not_directory.write_text("x", encoding="utf-8")
            result = transition_relaymem_slp_queue_state(
                _request(record), queue_root=str(not_directory), enabled=True,
            )
            assert result.status == "write_failed"
            assert "queue_root_not_directory" in result.blocked_reasons
            real = parent / "real"
            real.mkdir()
            link = parent / "queue-link"
            link.symlink_to(real, target_is_directory=True)
            result = transition_relaymem_slp_queue_state(
                _request(record), queue_root=str(link), enabled=True,
            )
            assert result.status == "write_failed"
            assert "queue_root_symlink_blocked" in result.blocked_reasons

        corrupt_cases: list[tuple[bytes, str]] = []
        corrupt_cases.append((b"\xff\xfe", "queue_record_malformed_utf8"))
        corrupt_cases.append((b'{"broken":', "queue_record_malformed_json"))
        corrupt_cases.append((b'{"x":1,"x":2}', "queue_record_duplicate_json_key"))
        corrupt_cases.append((json.dumps(record).encode("utf-8"), "queue_record_noncanonical_json"))
        unknown = dict(record); unknown["unexpected"] = True
        corrupt_cases.append((queue_state._canonical_json_bytes(unknown), "durable_job_shape_mismatch"))
        missing = dict(record); missing.pop("failure_class")
        corrupt_cases.append((queue_state._canonical_json_bytes(missing), "durable_job_shape_mismatch"))
        wrong_schema = dict(record); wrong_schema["schema_version"] = "relaymem.slp_durable_job.v1"
        corrupt_cases.append((queue_state._canonical_json_bytes(wrong_schema), "durable_job_schema_mismatch"))
        bool_counter = dict(record); bool_counter["attempt_count"] = True
        corrupt_cases.append((queue_state._canonical_json_bytes(bool_counter), "durable_job_attempt_count_invalid"))
        inconsistent_revision = dict(record)
        inconsistent_revision["attempt_count"] = 1
        inconsistent_revision["claim_generation"] = 1
        corrupt_cases.append((queue_state._canonical_json_bytes(inconsistent_revision), "durable_job_revision_generation_mismatch"))
        bad_queued = dict(record); bad_queued["lease_token"] = "lease-v0-invalid"
        corrupt_cases.append((queue_state._canonical_json_bytes(bad_queued), "durable_job_queued_claim_invariant_invalid"))
        for data, reason in corrupt_cases:
            with TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                path = root / _filename(record)
                path.write_bytes(data)
                before = path.read_bytes()
                result = _call(root, _request(record))
                assert result.status == "corrupt", (reason, result.status, result.blocked_reasons)
                assert reason in result.blocked_reasons, (reason, result.blocked_reasons)
                assert path.read_bytes() == before

        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / _filename(record)).write_bytes(b"x" * (queue_state._MAX_RECORD_BYTES + 1))
            result = _call(root, _request(record))
            assert result.status == "corrupt"
            assert "queue_record_size_exceeded" in result.blocked_reasons

        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            external = root / "external"
            external.write_bytes(queue_state._canonical_json_bytes(record))
            (root / _filename(record)).symlink_to(external)
            result = _call(root, _request(record))
            assert result.status == "corrupt"
            assert "queue_record_symlink_blocked" in result.blocked_reasons
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / _filename(record)).mkdir()
            result = _call(root, _request(record))
            assert result.status == "corrupt"
            assert "queue_record_unexpected_file_type" in result.blocked_reasons
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, record)
            os.link(path, root / "second-link")
            result = _call(root, _request(record))
            assert result.status == "corrupt"
            assert "queue_record_hardlink_count_invalid" in result.blocked_reasons

        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, record)
            wrong_revision = _call(root, _request(record, expected_record_revision=1))
            assert wrong_revision.status == "conflict"
            assert "record_revision_mismatch" in wrong_revision.blocked_reasons
            wrong_state_request = RelayMEMSLPQueueTransitionRequest(
                transition_kind="renew_lease",
                job_id=str(record["job_id"]),
                dispatch_idempotency_key=str(record["dispatch_idempotency_key"]),
                expected_record_revision=0,
                expected_state="claimed",
                claim_owner="worker-secure",
                claim_generation=0,
                lease_token="lease-v0-not-current",
                lease_duration_seconds=30,
            )
            wrong_state = _call(root, wrong_state_request)
            assert wrong_state.status == "conflict"
            assert "record_state_mismatch" in wrong_state.blocked_reasons

            claimed = _claim(root, record)
            queue_state._now_utc = lambda: base_now + timedelta(seconds=1)
            common = {
                "claim_owner": claimed["claim_owner"],
                "claim_generation": claimed["claim_generation"],
                "lease_token": claimed["lease_token"],
                "lease_duration_seconds": 30,
            }
            wrong_owner = _call(root, _request(claimed, "renew_lease", **{**common, "claim_owner": "worker-other"}))
            assert wrong_owner.status == "conflict"
            assert "claim_owner_mismatch" in wrong_owner.blocked_reasons
            wrong_generation = _call(root, _request(claimed, "renew_lease", **{**common, "claim_generation": 99}))
            assert wrong_generation.status == "conflict"
            assert "claim_generation_mismatch" in wrong_generation.blocked_reasons
            wrong_token = _call(root, _request(claimed, "renew_lease", **{**common, "lease_token": "lease-v0-wrong"}))
            assert wrong_token.status == "conflict"
            assert "lease_token_mismatch" in wrong_token.blocked_reasons
            assert _read(path) == claimed

        delayed = _record(run_id="delayed", lineage="f" * 64)
        delayed["retry_not_before"] = "2026-06-22T02:01:00.000000Z"
        delayed["retry_class"] = "transient_backend"
        delayed["failure_class"] = "backend_unavailable"
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, delayed)
            queue_state._now_utc = lambda: base_now + timedelta(seconds=59, microseconds=999999)
            before = _call(root, _request(delayed))
            assert before.status == "not_ready"
            queue_state._now_utc = lambda: base_now + timedelta(minutes=1)
            at = _call(root, _request(delayed))
            assert at.status == "applied"
            assert _read(path)["state"] == "claimed"

        stale = _record(run_id="stale-sec", lineage="1" * 64)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, stale)
            queue_state._now_utc = lambda: base_now
            claimed = _claim(root, stale)
            expiry = datetime.fromisoformat(str(claimed["lease_expires_at"])[:-1] + "+00:00")
            stale_request = _request(
                claimed,
                "stale_recovery",
                claim_owner="not-the-owner",
                lease_token=claimed["lease_token"],
            )
            queue_state._now_utc = lambda: expiry - timedelta(microseconds=1)
            assert _call(root, stale_request).status == "not_ready"
            queue_state._now_utc = lambda: expiry
            exact = _call(root, stale_request)
            assert exact.status == "applied"
            recovered = _read(path)
            assert recovered["state"] == "queued"

        stale_after = _record(run_id="stale-after", lineage="2" * 64)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, stale_after)
            queue_state._now_utc = lambda: base_now
            claimed = _claim(root, stale_after)
            expiry = datetime.fromisoformat(str(claimed["lease_expires_at"])[:-1] + "+00:00")
            queue_state._now_utc = lambda: expiry + timedelta(microseconds=1)
            after = _call(root, _request(
                claimed, "stale_recovery", claim_owner="ignored", lease_token=claimed["lease_token"],
            ))
            assert after.status == "applied"
            assert _read(path)["record_revision"] == 2

        overflow = _record(run_id="overflow", lineage="3" * 64)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, overflow)
            queue_state._now_utc = lambda: datetime(9999, 12, 31, 23, 59, 59, 900000, tzinfo=timezone.utc)
            result = _call(root, _request(overflow, lease_duration_seconds=1))
            assert result.status == "blocked"
            assert "lease_timestamp_overflow" in result.blocked_reasons
            assert _read(path) == overflow

        locked = _record(run_id="locked", lineage="4" * 64)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, locked)
            lock_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                queue_state._now_utc = lambda: base_now
                result = _call(root, _request(locked))
                assert result.status == "blocked"
                assert "queue_lock_busy" in result.blocked_reasons
                assert _read(path) == locked
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)

        cas = _record(run_id="cas", lineage="5" * 64)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, cas)
            def mutate_then_compare(root_fd: int, filename: str, snapshot):
                changed = dict(snapshot.record)
                changed["updated_at"] = "2026-06-22T00:00:01.000000Z"
                path.write_bytes(queue_state._canonical_json_bytes(changed))
                return original_reopen(root_fd, filename, snapshot)
            queue_storage.reopen_and_compare = mutate_then_compare
            queue_state._now_utc = lambda: base_now
            result = _call(root, _request(cas))
            assert result.status == "conflict"
            assert "queue_record_bytes_changed" in result.blocked_reasons
            assert _read(path)["state"] == "queued"
            assert not list(root.glob(".relay-slp-state-*.tmp"))
            queue_storage.reopen_and_compare = original_reopen

        terminal = _record(run_id="terminal", lineage="6" * 64)
        terminal.update({
            "state": "dead_letter",
            "failure_class": "isolated_corrupt_dependency",
            "terminal_reason_id": "later_policy_isolation",
        })
        assert not queue_state._validate_record_mapping(terminal)
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = _write(root, terminal)
            request = RelayMEMSLPQueueTransitionRequest(
                transition_kind="commit_terminal",
                job_id=str(terminal["job_id"]),
                dispatch_idempotency_key=str(terminal["dispatch_idempotency_key"]),
                expected_record_revision=0,
                expected_state="dead_letter",
                claim_generation=0,
                terminal_state="cancelled",
                terminal_reason_id="must_not_change",
            )
            result = _call(root, request)
            assert result.status == "blocked"
            assert "terminal_state_immutable" in result.blocked_reasons
            assert _read(path) == terminal

        print("Phase 6-B3 queue state security smoke: ok")
    finally:
        queue_state._now_utc = original_now
        queue_storage.reopen_and_compare = original_reopen


if __name__ == "__main__":
    main()
