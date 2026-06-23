"""Test-only support for Phase 6-C1-5 smokes."""
from __future__ import annotations

import runpy
from pathlib import Path

from relaylm.relaymem_slp_durable_runtime_enqueue import (
    apply_relaymem_slp_durable_runtime_enqueue,
)
from relaylm.relaymem_slp_primary_worker import (
    REQUEST_SCHEMA,
    RelayMEMSLPPrimaryWorkerRequest,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm.relaymem_slp_protected_source_store import (
    RelayMEMSLPDurableProtectedSourceStore,
)

from relaylm_phase6c1_primary_worker_test_support import require

REPO_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME = runpy.run_path(
    str(REPO_ROOT / "scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py"),
    run_name="relaylm_phase6c1_durable_source_support",
)
CHARACTER_ID = _RUNTIME["CHARACTER_ID"]
finalized = _RUNTIME["finalized"]
claim = _RUNTIME["claim"]
PRIVATE_TOKENS = tuple(
    _RUNTIME[name]
    for name in (
        "USER_CANARY", "ASSISTANT_CANARY", "SUMMARY_CANARY",
        "NAMESPACE_CANARY", "RUN_ID", "SESSION_ID",
    )
) + ("slp-dispatch-v0:", "slp-job-v0:")


def artifact_path(root: Path) -> Path:
    matches = list(root.glob("protected-source-v0-*.json"))
    require(len(matches) == 1, ("artifact cardinality", [p.name for p in matches]))
    return matches[0]


def assert_content_free(value: object) -> None:
    text = repr(value)
    for token in PRIVATE_TOKENS:
        require(token not in text, ("protected leak", token))


def worker_request(
    queue_root: Path, memory_root: Path, claimed: dict[str, object], prepared: object
) -> RelayMEMSLPPrimaryWorkerRequest:
    require(getattr(prepared, "status", None) == "prepared", prepared)
    source = getattr(prepared, "source", None)
    scope = getattr(prepared, "request_scope", None)
    require(source is not None and scope is not None, prepared)
    return RelayMEMSLPPrimaryWorkerRequest(
        schema_version=REQUEST_SCHEMA,
        runtime_private=True,
        content_included=True,
        claimed_record=dict(claimed),
        worker_source=source,
        request_scope=scope,
        queue_root=str(queue_root),
        store_root=str(memory_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
        lease_duration_seconds=300,
        retry_not_before=None,
    )


def apply_durable(
    queue_root: Path, protected_root: Path,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry,
    *, source_result: object | None = None,
):
    return apply_relaymem_slp_durable_runtime_enqueue(
        source_result or finalized(),
        registry=registry,
        source_store=RelayMEMSLPDurableProtectedSourceStore(str(protected_root)),
        queue_root=str(queue_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
