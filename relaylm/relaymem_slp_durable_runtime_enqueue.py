"""Crash-consistent I1-B enqueue adapter for Phase 6-C1-5.

The canonical I1-B helper is first executed in dry-run mode to obtain the exact
B1 identity and protected capture.  The capture is durably committed before B2
publishes the content-free queue record.  The canonical apply helper then runs
unchanged, preserving B2 and process-local registry ownership.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

from .pipeline_node_result import PipelineNodeResult, build_pipeline_node_result
from .relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from .relaymem_slp_protected_source_store import (
    ARTIFACT_SCHEMA,
    RelayMEMSLPDurableProtectedSourceStore,
    RelayMEMSLPProtectedSourceStoreResult,
)
from .relaymem_slp_queue_record import dedupe, strict_bool
from .relaymem_slp_runtime_enqueue import (
    RelayMEMSLPRuntimeEnqueueResult,
    apply_relaymem_slp_runtime_enqueue,
)

DURABLE_RUNTIME_ENQUEUE_SCHEMA = "relaymem.slp_durable_runtime_enqueue.v0"
DURABLE_RUNTIME_ENQUEUE_PROJECTION_SCHEMA = (
    "relaymem.slp_durable_runtime_enqueue_projection.v0"
)
_MAX_REASONS = 32

DurableRuntimeEnqueueStatus = Literal[
    "disabled",
    "invalid_input",
    "blocked",
    "dry_run_ready",
    "source_persistence_failed",
    "enqueue_failed",
    "enqueued",
    "duplicate_existing",
    "process_local_cache_degraded",
]


@dataclass(frozen=True, repr=False)
class RelayMEMSLPDurableRuntimeEnqueueResult:
    status: DurableRuntimeEnqueueStatus
    enabled: bool
    dry_run_only: bool
    apply_enabled: bool
    restart_complete: bool
    source_persisted_before_enqueue: bool
    blocked_reasons: tuple[str, ...]
    runtime_result: RelayMEMSLPRuntimeEnqueueResult = field(
        repr=False, compare=False
    )
    source_store_result: RelayMEMSLPProtectedSourceStoreResult | None = field(
        default=None, repr=False, compare=False
    )
    orphan_cleanup_result: RelayMEMSLPProtectedSourceStoreResult | None = field(
        default=None, repr=False, compare=False
    )

    def __repr__(self) -> str:
        return (
            "RelayMEMSLPDurableRuntimeEnqueueResult("
            f"status={self.status!r}, restart_complete={self.restart_complete!r}, "
            "protected_content_omitted=True)"
        )

    def to_log_dict(self) -> dict[str, object]:
        store = self.source_store_result
        cleanup = self.orphan_cleanup_result
        return {
            "schema_version": DURABLE_RUNTIME_ENQUEUE_PROJECTION_SCHEMA,
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "raw_text_included": False,
            "raw_messages_included": False,
            "governed_title_included": False,
            "governed_summary_included": False,
            "identifier_values_included": False,
            "namespace_value_included": False,
            "lineage_fingerprint_included": False,
            "source_digest_included": False,
            "queue_path_included": False,
            "protected_source_path_included": False,
            "exception_text_included": False,
            "status": self.status,
            "enabled": self.enabled,
            "dry_run_only": self.dry_run_only,
            "apply_enabled": self.apply_enabled,
            "restart_complete_source_persistence": self.restart_complete,
            "source_persisted_before_enqueue": self.source_persisted_before_enqueue,
            "source_store_status": store.status if store is not None else "not_used",
            "source_store_durable": bool(store is not None and store.durable),
            "source_store_available": bool(
                store is not None and store.source_available
            ),
            "orphan_cleanup_status": (
                cleanup.status if cleanup is not None else "not_required"
            ),
            "process_local_cache_retained": bool(
                self.runtime_result.source_retention_result is not None
                and self.runtime_result.source_retention_result.retained
            ),
            "enqueue_status": (
                self.runtime_result.enqueue_result.status
                if self.runtime_result.enqueue_result is not None
                else "not_attempted"
            ),
            "worker_invoked": False,
            "b3_claim_performed": False,
            "writes_memory": False,
            "changes_visible_response": False,
            "blocked_reason_ids": list(self.blocked_reasons),
        }


def apply_relaymem_slp_durable_runtime_enqueue(
    finalized_turn_source_result: object,
    *,
    registry: RelayMEMSLPPrimaryWorkerSourceRegistry | None,
    source_store: RelayMEMSLPDurableProtectedSourceStore | None,
    queue_root: str | None,
    enabled: bool = False,
    dry_run_only: bool = True,
    apply_enabled: bool = False,
) -> RelayMEMSLPDurableRuntimeEnqueueResult:
    """Persist protected source before canonical B2 queue publication."""

    enabled_value, enabled_reasons = strict_bool(enabled, "enabled_invalid")
    dry_value, dry_reasons = strict_bool(dry_run_only, "dry_run_only_invalid")
    apply_value, apply_reasons = strict_bool(apply_enabled, "apply_enabled_invalid")
    gate_reasons = dedupe((*enabled_reasons, *dry_reasons, *apply_reasons))
    if gate_reasons or not enabled_value or dry_value or not apply_value:
        delegated = apply_relaymem_slp_runtime_enqueue(
            finalized_turn_source_result,
            registry=registry,
            queue_root=queue_root,
            enabled=enabled,
            dry_run_only=dry_run_only,
            apply_enabled=apply_enabled,
        )
        if gate_reasons:
            return _result(
                "invalid_input", delegated, enabled_value, dry_value, apply_value, gate_reasons
            )
        if not enabled_value:
            return _result("disabled", delegated, False, dry_value, apply_value, ())
        if dry_value:
            return _result(
                "dry_run_ready" if delegated.status == "dry_run_ready" else "blocked",
                delegated, True, True, apply_value, delegated.blocked_reasons,
            )
        return _result(
            "blocked", delegated, True, False, False,
            delegated.blocked_reasons or ("apply_gate_incomplete",),
        )

    preparation = apply_relaymem_slp_runtime_enqueue(
        finalized_turn_source_result,
        registry=registry,
        queue_root=queue_root,
        enabled=True,
        dry_run_only=True,
        apply_enabled=False,
    )
    if preparation.source_scope is not None:
        preparation.source_scope.close()
    if type(registry) is not RelayMEMSLPPrimaryWorkerSourceRegistry:
        return _result(
            "source_persistence_failed", preparation, True, False, True,
            ("exact_source_registry_required",),
        )
    if type(source_store) is not RelayMEMSLPDurableProtectedSourceStore:
        return _result(
            "source_persistence_failed", preparation, True, False, True,
            ("exact_durable_protected_source_store_required",),
        )

    dispatch = preparation.dispatch_result
    payload = preparation.protected_source_payload
    source_result = preparation.finalized_turn_source_result
    source = source_result.source if source_result is not None else None
    if (
        preparation.status != "dry_run_ready"
        or dispatch is None
        or dispatch.durable_job is None
        or type(payload) is not dict
        or source is None
    ):
        blocked = replace(
            preparation,
            status="source_retention_failed",
            dry_run_only=False,
            apply_enabled=True,
            failure_stage="source_retention",
            blocked_reasons=preparation.blocked_reasons
            or ("durable_source_preparation_failed",),
        )
        return _result(
            "source_persistence_failed",
            blocked,
            True,
            False,
            True,
            blocked.blocked_reasons,
        )

    persisted = source_store.persist(
        source_payload=payload,
        durable_job=dispatch.durable_job,
        character_id=source.character_id,
    )
    if persisted.status not in {"published_new", "duplicate_existing"}:
        blocked = replace(
            preparation,
            status="source_retention_failed",
            dry_run_only=False,
            apply_enabled=True,
            failure_stage="source_retention",
            blocked_reasons=persisted.blocked_reasons
            or ("durable_protected_source_persistence_failed",),
        )
        return _result(
            "source_persistence_failed",
            blocked,
            True,
            False,
            True,
            blocked.blocked_reasons,
            source_store_result=persisted,
        )

    applied = apply_relaymem_slp_runtime_enqueue(
        finalized_turn_source_result,
        registry=registry,
        queue_root=queue_root,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    enqueue = applied.enqueue_result
    queue_published = bool(
        enqueue is not None
        and enqueue.status in {"enqueued_new", "duplicate_existing"}
    )
    cleanup: RelayMEMSLPProtectedSourceStoreResult | None = None
    if not queue_published and persisted.status == "published_new":
        cleanup = source_store.discard_unqueued(
            source_payload=payload,
            durable_job=dispatch.durable_job,
            character_id=source.character_id,
        )
    if not queue_published:
        reasons = dedupe(
            (
                *applied.blocked_reasons,
                *(cleanup.blocked_reasons if cleanup is not None else ()),
            )
        ) or ("durable_enqueue_failed",)
        return _result(
            "enqueue_failed",
            applied,
            True,
            False,
            True,
            reasons,
            source_store_result=persisted,
            orphan_cleanup_result=cleanup,
        )

    restart_complete = True
    if applied.status in {"enqueued", "duplicate_existing"}:
        status: DurableRuntimeEnqueueStatus = applied.status
    elif applied.status == "source_retention_failed":
        status = "process_local_cache_degraded"
    else:
        status = "enqueued" if enqueue.status == "enqueued_new" else "duplicate_existing"
    nonfatal_reasons = (
        applied.blocked_reasons if status == "process_local_cache_degraded" else ()
    )
    return _result(
        status,
        applied,
        True,
        False,
        True,
        nonfatal_reasons,
        restart_complete=restart_complete,
        source_persisted_before_enqueue=True,
        source_store_result=persisted,
    )


def build_relaymem_slp_durable_runtime_enqueue_failure_result(
    runtime_result: RelayMEMSLPRuntimeEnqueueResult,
    reason_id: str = "durable_runtime_enqueue_background_failed",
) -> RelayMEMSLPDurableRuntimeEnqueueResult:
    safe_reason = (
        reason_id
        if type(reason_id) is str and reason_id and len(reason_id) <= 128
        else "durable_runtime_enqueue_background_failed"
    )
    return _result(
        "enqueue_failed",
        runtime_result,
        True,
        False,
        True,
        (safe_reason,),
    )


def build_relaymem_slp_durable_runtime_enqueue_node_result(
    result: RelayMEMSLPDurableRuntimeEnqueueResult,
) -> PipelineNodeResult:
    node_status = {
        "disabled": "skipped",
        "invalid_input": "failed",
        "blocked": "blocked",
        "source_persistence_failed": "failed",
        "enqueue_failed": "failed",
        "process_local_cache_degraded": "diagnostic_only",
    }.get(result.status, "diagnostic_only")
    projection = result.to_log_dict()
    return build_pipeline_node_result(
        node_name="relaymem_slp_durable_runtime_enqueue",
        status=node_status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=projection,
        artifacts=[
            {
                "artifact_name": "relaymem_slp_durable_protected_source",
                "schema_version": ARTIFACT_SCHEMA,
                "present": projection["source_store_available"],
                "content_free": True,
                "runtime_private": True,
                "protected_payload_omitted": True,
                "restart_complete": result.restart_complete,
                "persisted_before_enqueue": result.source_persisted_before_enqueue,
                "path_included": False,
                "digest_included": False,
                "identifier_values_included": False,
                "worker_invoked": False,
                "writes_memory": False,
            }
        ],
    )


def _result(
    status: DurableRuntimeEnqueueStatus,
    runtime_result: RelayMEMSLPRuntimeEnqueueResult,
    enabled: bool,
    dry_run_only: bool,
    apply_enabled: bool,
    reasons: tuple[str, ...],
    *,
    restart_complete: bool = False,
    source_persisted_before_enqueue: bool = False,
    source_store_result: RelayMEMSLPProtectedSourceStoreResult | None = None,
    orphan_cleanup_result: RelayMEMSLPProtectedSourceStoreResult | None = None,
) -> RelayMEMSLPDurableRuntimeEnqueueResult:
    return RelayMEMSLPDurableRuntimeEnqueueResult(
        status=status,
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        restart_complete=restart_complete,
        source_persisted_before_enqueue=source_persisted_before_enqueue,
        blocked_reasons=dedupe(reasons)[:_MAX_REASONS],
        runtime_result=runtime_result,
        source_store_result=source_store_result,
        orphan_cleanup_result=orphan_cleanup_result,
    )


__all__ = [
    "DURABLE_RUNTIME_ENQUEUE_PROJECTION_SCHEMA",
    "DURABLE_RUNTIME_ENQUEUE_SCHEMA",
    "RelayMEMSLPDurableRuntimeEnqueueResult",
    "apply_relaymem_slp_durable_runtime_enqueue",
    "build_relaymem_slp_durable_runtime_enqueue_failure_result",
    "build_relaymem_slp_durable_runtime_enqueue_node_result",
]
