from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import relaylm.relaymem_slp_queue_state as queue_state
from relaylm.config import RelayLMConfig
from relaylm.relaymem_slp_scheduler_operations import (
    SchedulerCancellationToken,
    run_relaymem_slp_scheduler_operational_controls_once,
    validate_scheduler_operational_controls_config,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _base_config(**overrides: Any) -> RelayLMConfig:
    raw: dict[str, Any] = {
        "backends": {"local": {"base_url": "http://127.0.0.1:8000/v1"}},
        "model_routes": {"relaylm-default": {"backend": "local"}},
    }
    raw.update(overrides)
    return RelayLMConfig.model_validate(raw)


def _initial_record() -> dict[str, object]:
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
        "run_id": "run-1",
        "turn_index": 4,
        "session_id": "session-1",
        "namespace": "default",
        "source_count": 1,
        "source_lineage_fingerprint": "a" * 64,
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
    require(not queue_state._validate_record_mapping(record), "base record invalid")
    return record


def _stale_claimed_record() -> dict[str, object]:
    record = _initial_record()
    record.update({
        "state": "claimed",
        "record_revision": 1,
        "updated_at": "2026-06-22T00:00:01.000000Z",
        "attempt_count": 1,
        "claim_generation": 1,
        "claim_owner": "worker-a",
        "lease_token": "lease-v0-" + "b" * 64,
        "lease_acquired_at": "2026-06-22T00:00:01.000000Z",
        "lease_expires_at": "2026-06-22T00:00:02.000000Z",
    })
    require(not queue_state._validate_record_mapping(record), "stale record invalid")
    return record


def _write(root: Path, record: dict[str, object]) -> Path:
    path = root / queue_state._record_filename(str(record["dispatch_idempotency_key"]))
    path.write_bytes(queue_state._canonical_json_bytes(record))
    return path


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains(value: object, target: object) -> bool:
    if value == target:
        return True
    if isinstance(value, dict):
        return any(_contains(item, target) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains(item, target) for item in value)
    return False


def main() -> int:
    disabled = run_relaymem_slp_scheduler_operational_controls_once(config=_base_config())
    require(disabled.status == "disabled", disabled)
    require(disabled.scheduler_round_invoked is False, disabled.projection())

    dry_run_config = _base_config(
        relaymem_local_scheduler_operational_controls_enabled=True,
        relaymem_local_scheduler_operational_controls_dry_run_only=True,
        relaymem_local_scheduler_operational_controls_apply_enabled=False,
    )
    mode, stale_mode, reasons = validate_scheduler_operational_controls_config(dry_run_config)
    require((mode, stale_mode, reasons) == ("dry_run", "disabled", ()), (mode, stale_mode, reasons))
    dry_run = run_relaymem_slp_scheduler_operational_controls_once(config=dry_run_config)
    require(dry_run.status == "dry_run_ready", dry_run.projection())
    require(dry_run.scheduler_round_invoked is True, dry_run.projection())
    require(dry_run.projection()["scheduler_policy_status"] == "policy_disabled", dry_run.projection())

    cancelled = run_relaymem_slp_scheduler_operational_controls_once(
        config=dry_run_config,
        cancellation=SchedulerCancellationToken(lambda: True),
    )
    require(cancelled.status == "cancelled_before_start", cancelled.projection())
    require(cancelled.scheduler_round_invoked is False, cancelled.projection())

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        record = _stale_claimed_record()
        path = _write(root, record)
        original = path.read_bytes()
        stale_dry_config = _base_config(
            relaymem_slp_queue_root=str(root),
            relaymem_local_scheduler_operational_controls_enabled=True,
            relaymem_local_scheduler_operational_controls_dry_run_only=True,
            relaymem_local_scheduler_operational_controls_apply_enabled=False,
            relaymem_local_scheduler_stale_recovery_enabled=True,
            relaymem_local_scheduler_stale_recovery_dry_run_only=True,
            relaymem_local_scheduler_stale_recovery_apply_enabled=False,
        )
        stale_dry = run_relaymem_slp_scheduler_operational_controls_once(
            config=stale_dry_config,
            now=datetime(2026, 6, 22, 0, 0, 3, tzinfo=timezone.utc),
        )
        require(stale_dry.stale_recovery_status == "stale_recovery_dry_run_ready", stale_dry.projection())
        require(path.read_bytes() == original, "dry-run mutated queue record")
        projection = stale_dry.projection()
        for private_value in (
            str(root),
            str(record["job_id"]),
            str(record["dispatch_idempotency_key"]),
            str(record["lease_token"]),
            str(record["lease_expires_at"]),
        ):
            require(not _contains(projection, private_value), projection)

    with TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        path = _write(root, _stale_claimed_record())
        stale_apply_config = _base_config(
            relaymem_slp_queue_root=str(root),
            relaymem_local_scheduler_operational_controls_enabled=True,
            relaymem_local_scheduler_operational_controls_dry_run_only=False,
            relaymem_local_scheduler_operational_controls_apply_enabled=True,
            relaymem_local_scheduler_stale_recovery_enabled=True,
            relaymem_local_scheduler_stale_recovery_dry_run_only=False,
            relaymem_local_scheduler_stale_recovery_apply_enabled=True,
        )
        applied = run_relaymem_slp_scheduler_operational_controls_once(
            config=stale_apply_config,
            now=datetime(2026, 6, 22, 0, 0, 3, tzinfo=timezone.utc),
        )
        require(applied.status == "completed", applied.projection())
        require(applied.stale_recovery_status == "stale_recovery_attempted", applied.projection())
        require(applied.stale_recovery_applied is True, applied.projection())
        updated = _read(path)
        require(updated["state"] == "queued", updated)
        require(updated["claim_owner"] == "", updated)
        require(updated["lease_token"] == "", updated)
        require(updated["retry_class"] == "stale_lease_recovery", updated)
        require(updated["failure_class"] == "stale_lease_expired", updated)

    print("ok O1E disabled/dry-run/cancellation/stale-recovery controls")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
