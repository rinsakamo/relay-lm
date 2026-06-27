"""Shared content-free fixtures for O1F operational-validation smokes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from relaylm.config import RelayLMConfig
import relaylm.relaymem_slp_queue_state as queue_state
from relaylm.relaymem_slp_scheduler_operational_validation import FORBIDDEN_PUBLIC_TOKENS

CANARY = "O1F_PRIVATE_CONTENT_CANARY_9c14d7"
PATH_CANARY = "/private/o1f/root/never-project"
RAW_EXCEPTION_CANARY = "O1F_RAW_EXCEPTION_CANARY_359b7a"
FORBIDDEN = FORBIDDEN_PUBLIC_TOKENS + (
    CANARY,
    PATH_CANARY,
    RAW_EXCEPTION_CANARY,
    "job_id",
    "dispatch_idempotency_key",
    "lease_token",
    "claim_owner",
    "protected_source_body",
    "memory_content",
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def base_config(**overrides: Any) -> RelayLMConfig:
    raw: dict[str, Any] = {
        "backends": {"local": {"base_url": "http://127.0.0.1:1234/v1"}},
        "model_routes": {"relaylm-default": {"backend": "local"}},
    }
    raw.update(overrides)
    return RelayLMConfig.model_validate(raw)


def operational_config(*, mode: str = "dry_run", stale: str = "disabled", queue_root: Path | None = None, **overrides: Any) -> RelayLMConfig:
    triples = {
        "disabled": (False, True, False),
        "dry_run": (True, True, False),
        "apply": (True, False, True),
    }
    op_enabled, op_dry, op_apply = triples[mode]
    stale_enabled, stale_dry, stale_apply = triples[stale]
    raw: dict[str, Any] = {
        "relaymem_local_scheduler_operational_controls_enabled": op_enabled,
        "relaymem_local_scheduler_operational_controls_dry_run_only": op_dry,
        "relaymem_local_scheduler_operational_controls_apply_enabled": op_apply,
        "relaymem_local_scheduler_stale_recovery_enabled": stale_enabled,
        "relaymem_local_scheduler_stale_recovery_dry_run_only": stale_dry,
        "relaymem_local_scheduler_stale_recovery_apply_enabled": stale_apply,
    }
    if queue_root is not None:
        raw["relaymem_slp_queue_root"] = str(queue_root)
    raw.update(overrides)
    return base_config(**raw)


def initial_record() -> dict[str, object]:
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
        "run_id": "run_o1f",
        "turn_index": 7,
        "session_id": "session_o1f",
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


def stale_claimed_record() -> dict[str, object]:
    record = initial_record()
    record.update({
        "state": "claimed",
        "record_revision": 1,
        "updated_at": "2026-06-22T00:00:01.000000Z",
        "attempt_count": 1,
        "claim_generation": 1,
        "claim_owner": "worker_o1f",
        "lease_token": "lease-v0-" + "b" * 64,
        "lease_acquired_at": "2026-06-22T00:00:01.000000Z",
        "lease_expires_at": "2026-06-22T00:00:02.000000Z",
    })
    require(not queue_state._validate_record_mapping(record), "stale record invalid")
    return record


def terminal_record(state: str = "succeeded") -> dict[str, object]:
    record = initial_record()
    record.update({
        "state": state,
        "record_revision": 1,
        "updated_at": "2026-06-22T00:00:01.000000Z",
        "terminal_reason_id": "terminal_o1f",
    })
    require(not queue_state._validate_record_mapping(record), "terminal record invalid")
    return record


def write_record(root: Path, record: dict[str, object]) -> Path:
    path = root / queue_state._record_filename(str(record["dispatch_idempotency_key"]))
    path.write_bytes(queue_state._canonical_json_bytes(record))
    return path


def read_record(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def contains(value: object, target: object) -> bool:
    if value == target:
        return True
    if isinstance(value, dict):
        return any(contains(item, target) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains(item, target) for item in value)
    return False


def assert_public_result_safe(result: object) -> str:
    projection = result.projection()
    encoded = json.dumps(projection, ensure_ascii=True, sort_keys=True)
    lowered = encoded.lower()
    for token in FORBIDDEN:
        require(token.lower() not in lowered, encoded)
        require(token.lower() not in repr(result).lower(), repr(result))
    return encoded


def sequence_probe(values: list[bool]) -> Callable[[], bool]:
    state = {"index": 0}

    def probe() -> bool:
        index = state["index"]
        state["index"] = index + 1
        if index >= len(values):
            return values[-1]
        return values[index]

    return probe
