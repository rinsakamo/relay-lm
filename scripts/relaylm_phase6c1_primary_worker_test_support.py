"""Test-only support for the Phase 6-C1-2 one-claimed-job worker smokes."""
from __future__ import annotations

import json
import runpy
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import relaylm.relaymem_slp_queue_state as queue_state
from relaylm.relaymem_primary_pipeline import RelayMEMPrimaryPipelineRequest
from relaylm.relaymem_slp_primary_worker import (
    REQUEST_SCHEMA,
    RelayMEMSLPPrimaryWorkerRequest,
)
from relaylm.relaymem_slp_primary_worker_source import (
    RelayMEMSLPPrimaryWorkerSourceScope,
    build_relaymem_slp_primary_worker_source,
)
from relaylm.relaymem_slp_queue_record import canonical_json_bytes, record_filename

REPO_ROOT = Path(__file__).resolve().parents[1]
_COMPOSE = runpy.run_path(
    str(REPO_ROOT / "scripts/relaylm_relaymem_primary_pipeline_smoke.py"),
    run_name="relaylm_phase6c1_primary_worker_compose_support",
)
claimed_record = _COMPOSE["claimed_record"]
source_payload = _COMPOSE["source_payload"]
prepare_store = _COMPOSE["prepare_store"]
m3g_result = _COMPOSE["_m3g"]
m3h_result = _COMPOSE["_m3h"]
CANARIES = (
    _COMPOSE["CANARY_SOURCE"],
    _COMPOSE["CANARY_SUMMARY"],
    _COMPOSE["CANARY_NAMESPACE"],
    _COMPOSE["CANARY_MEMORY_KEY"],
    _COMPOSE["CANARY_STORE_PATH"],
    _COMPOSE["LINEAGE"],
    "lease-c1-compose-secret",
    "slp-dispatch-v0:",
    "slp-job-v0:",
)
FIXED_NOW = datetime(2026, 6, 23, 0, 1, tzinfo=timezone.utc)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def write_record(queue_root: Path, record: dict[str, object]) -> Path:
    path = queue_root / record_filename(str(record["dispatch_idempotency_key"]))
    path.write_bytes(canonical_json_bytes(record))
    return path


def read_record(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(type(value) is dict, "queue record shape")
    return value


@contextmanager
def fixed_queue_time(now: datetime = FIXED_NOW) -> Iterator[None]:
    original_now = queue_state._now_utc
    queue_state._now_utc = lambda: now
    try:
        yield
    finally:
        queue_state._now_utc = original_now


def build_request(
    queue_root: Path,
    store_root: Path,
    *,
    record: dict[str, object] | None = None,
    scene_type: str = "design_talk",
    enabled: bool = True,
    dry_run_only: bool = False,
    apply_enabled: bool = True,
    lease_duration_seconds: int = 300,
    retry_not_before: str | None = None,
) -> tuple[RelayMEMSLPPrimaryWorkerRequest, RelayMEMSLPPrimaryWorkerSourceScope]:
    exact_record = dict(record or claimed_record())
    scope = RelayMEMSLPPrimaryWorkerSourceScope()
    built = build_relaymem_slp_primary_worker_source(
        source_payload(exact_record, scene_type=scene_type),
        claimed_record=exact_record,
        request_scope=scope,
        enabled=True,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
    )
    require(built.source is not None, built.to_log_dict())
    request = RelayMEMSLPPrimaryWorkerRequest(
        schema_version=REQUEST_SCHEMA,
        runtime_private=True,
        content_included=True,
        claimed_record=exact_record,
        worker_source=built.source,
        request_scope=scope,
        queue_root=str(queue_root),
        store_root=str(store_root),
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        lease_duration_seconds=lease_duration_seconds,
        retry_not_before=retry_not_before,
    )
    return request, scope


def with_record(request: RelayMEMSLPPrimaryWorkerRequest, record: dict[str, object]):
    return replace(request, claimed_record=dict(record))


def full_m3h(classification: str, *, lock: bool = False) -> dict[str, object]:
    if lock:
        value = m3h_result("recovery_not_required")
        value.update(
            status="blocked",
            source_status="applied",
            store_state="not_evaluated",
            recovery_classification="not_evaluated",
            blocked_reasons=["primary_reconciliation_recovery_lock_unavailable"],
        )
        projection = {
            "page_verified": False,
            "index_state": "not_checked",
            "log_state": "not_checked",
            "cleanup_artifacts_present": False,
        }
    else:
        value = m3h_result(classification)
        partial = classification == "retry_reconciliation"
        projection = {
            "page_verified": True,
            "index_state": "proposed",
            "log_state": "expected" if partial else "proposed",
            "cleanup_artifacts_present": False,
        }
    value["projection"] = projection
    return value


def assert_no_canary(value: object, *extra: object) -> None:
    text = repr(value)
    for token in (*CANARIES, *extra):
        if token:
            require(str(token) not in text, ("private leak", token))


def pipeline_request_from_worker(
    request: RelayMEMSLPPrimaryWorkerRequest,
) -> RelayMEMPrimaryPipelineRequest:
    return RelayMEMPrimaryPipelineRequest(
        schema_version="relaymem.primary_pipeline_request.v0",
        runtime_private=True,
        content_included=True,
        worker_source=request.worker_source,
        claimed_record=request.claimed_record,
        request_scope=request.request_scope,
        store_root=request.store_root,
        enabled=request.enabled,
        dry_run_only=request.dry_run_only,
        apply_enabled=request.apply_enabled,
    )
