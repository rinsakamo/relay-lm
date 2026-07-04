"""Public RelayMEM Phase 6-C1-1 Primary MEM pipeline boundary.

The implementation remains runtime-private in the adjacent implementation
module. This facade fixes the exact public types, synchronizes testable M3
helper seams, and rejects non-canonical request modes or impossible result
ledgers before any public projection is produced.

Phase 6-C1-2 adds a minimal runtime-private checkpoint seam. The seam knows
nothing about queue roots, claims, leases, or B3 transitions; it only asks an
exact callback whether the next protected or durable side effect may begin.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from threading import RLock
from typing import Any, Literal

from . import _relaymem_primary_pipeline_impl as _impl
from ._relaymem_primary_pipeline_impl import (
    PROJECTION_SCHEMA,
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    STAGES,
    RelayMEMPrimaryPipelineProjection,
    RelayMEMPrimaryPipelineRequest,
    RelayMEMPrimaryPipelineResult,
    RelayMEMPrimaryPipelineStageResult,
)

PrimaryPipelineCheckpointName = Literal[
    "before_source_consumption",
    "before_m3e_page_writer",
    "before_m3g_reconciliation_apply",
]


@dataclass(frozen=True)
class RelayMEMPrimaryPipelineCheckpointResult:
    """Exact content-free permission returned by a runtime-private checkpoint."""

    allowed: bool
    reason_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelayMEMPrimaryPipelineCheckpointDenied:
    """Typed content-free checkpoint denial preserved across helper seams."""

    stage: str
    checkpoint: PrimaryPipelineCheckpointName
    reason_ids: tuple[str, ...]


PrimaryPipelineCheckpoint = Callable[
    [PrimaryPipelineCheckpointName], RelayMEMPrimaryPipelineCheckpointResult
]

# Preserve the existing module-level M3 seams. The functional and security
# smokes patch these exact names; execute synchronizes them into the private
# implementation immediately before each invocation.
build_relaymem_primary_formation_dry_run = (
    _impl.build_relaymem_primary_formation_dry_run
)
build_relaymem_primary_write_preflight_dry_run = (
    _impl.build_relaymem_primary_write_preflight_dry_run
)
build_relaymem_primary_page_candidate_dry_run = (
    _impl.build_relaymem_primary_page_candidate_dry_run
)
build_relaymem_primary_writer_handoff_preflight = (
    _impl.build_relaymem_primary_writer_handoff_preflight
)
apply_relaymem_primary_page_write = _impl.apply_relaymem_primary_page_write
build_relaymem_primary_index_log_reconciliation_preflight = (
    _impl.build_relaymem_primary_index_log_reconciliation_preflight
)
apply_relaymem_primary_index_log_reconciliation = (
    _impl.apply_relaymem_primary_index_log_reconciliation
)
audit_relaymem_primary_index_log_reconciliation_recovery = (
    _impl.audit_relaymem_primary_index_log_reconciliation_recovery
)

_HELPER_NAMES = (
    "build_relaymem_primary_write_preflight_dry_run",
    "build_relaymem_primary_page_candidate_dry_run",
    "build_relaymem_primary_writer_handoff_preflight",
    "apply_relaymem_primary_page_write",
    "build_relaymem_primary_index_log_reconciliation_preflight",
    "apply_relaymem_primary_index_log_reconciliation",
    "audit_relaymem_primary_index_log_reconciliation_recovery",
)
_CANONICAL_MODES = frozenset(
    {
        (False, True, False),
        (True, True, False),
        (True, False, True),
    }
)
_STAGE_STATUSES = frozenset(
    {
        "not_run",
        "completed",
        "blocked",
        "held",
        "retryable",
        "skipped_dry_run",
    }
)
_PIPELINE_STATUSES = frozenset(
    {
        "disabled",
        "invalid_input",
        "blocked",
        "held",
        "dry_run_ready",
        "recovery_not_required",
        "retry_reconciliation",
        "manual_confirmation_required",
        "journaled_recovery_candidate",
    }
)
_COMPOSE_LOCK = RLock()
_CURRENT_CANDIDATE_ID: str | None = None

_original_validate_request = _impl._validate_request
_original_project = _impl.project_relaymem_primary_pipeline


def _validate_request(
    value: object,
) -> tuple[RelayMEMPrimaryPipelineRequest | None, tuple[str, ...]]:
    request, reasons = _original_validate_request(value)
    if request is None:
        return None, reasons
    mode = (request.enabled, request.dry_run_only, request.apply_enabled)
    if mode not in _CANONICAL_MODES:
        return None, ("primary_pipeline_gate_mode_invalid",)
    return request, ()


def _validate_pipeline_result(result: object) -> RelayMEMPrimaryPipelineResult:
    if type(result) is not RelayMEMPrimaryPipelineResult:
        raise TypeError("exact RelayMEMPrimaryPipelineResult required")
    if (
        result.schema_version != RESULT_SCHEMA
        or result.runtime_private is not True
        or result.content_included is not True
    ):
        raise ValueError("primary pipeline result envelope invalid")
    if any(
        type(value) is not bool
        for value in (result.enabled, result.dry_run_only, result.apply_enabled)
    ):
        raise ValueError("primary pipeline result gate type invalid")
    if (
        result.enabled,
        result.dry_run_only,
        result.apply_enabled,
    ) not in _CANONICAL_MODES:
        raise ValueError("primary pipeline result gate mode invalid")
    if result.status not in _PIPELINE_STATUSES:
        raise ValueError("primary pipeline result status invalid")
    if type(result.stage_results) is not tuple or len(result.stage_results) != len(
        STAGES
    ):
        raise ValueError("primary pipeline stage ledger cardinality invalid")
    if tuple(item.stage for item in result.stage_results) != STAGES:
        raise ValueError("primary pipeline stage order invalid")

    executed_indexes: list[int] = []
    completed_indexes: list[int] = []
    for index, item in enumerate(result.stage_results):
        if type(item) is not RelayMEMPrimaryPipelineStageResult:
            raise ValueError("primary pipeline stage entry type invalid")
        if item.status not in _STAGE_STATUSES:
            raise ValueError("primary pipeline stage status invalid")
        if any(
            type(value) is not bool
            for value in (
                item.executed,
                item.completed,
                item.blocked,
                item.held,
                item.retryable,
                item.terminal,
            )
        ):
            raise ValueError("primary pipeline stage flag type invalid")
        if (
            type(item.reason_ids) is not tuple
            or _impl._reasons(item.reason_ids) != item.reason_ids
        ):
            raise ValueError("primary pipeline stage reason ids invalid")
        if item.status in {"not_run", "skipped_dry_run"} and (
            item.executed
            or item.completed
            or item.blocked
            or item.held
            or item.retryable
            or item.terminal
        ):
            raise ValueError("primary pipeline unexecuted stage flags invalid")
        if item.status == "completed" and (
            not item.executed or not item.completed
        ):
            raise ValueError("primary pipeline completed stage flags invalid")
        if item.status == "blocked" and (
            not item.executed or not item.blocked
        ):
            raise ValueError("primary pipeline blocked stage flags invalid")
        if item.status == "held" and (not item.executed or not item.held):
            raise ValueError("primary pipeline held stage flags invalid")
        if item.status == "retryable" and (
            not item.executed or not item.retryable
        ):
            raise ValueError("primary pipeline retryable stage flags invalid")
        if item.executed:
            executed_indexes.append(index)
        if item.completed:
            completed_indexes.append(index)

    if executed_indexes and executed_indexes != list(
        range(executed_indexes[-1] + 1)
    ):
        raise ValueError("primary pipeline executed stage order invalid")
    if completed_indexes and completed_indexes != list(
        range(completed_indexes[-1] + 1)
    ):
        raise ValueError("primary pipeline completed stage order invalid")
    if type(result.completed_stage_count) is not int or (
        result.completed_stage_count != len(completed_indexes)
    ):
        raise ValueError("primary pipeline completed stage count invalid")

    expected_last = STAGES[executed_indexes[-1]] if executed_indexes else None
    expected_completed = (
        STAGES[completed_indexes[-1]] if completed_indexes else None
    )
    if result.last_stage != expected_last:
        raise ValueError("primary pipeline last stage invalid")
    if result.last_completed_stage != expected_completed:
        raise ValueError("primary pipeline last completed stage invalid")
    if (
        type(result.reason_ids) is not tuple
        or _impl._reasons(result.reason_ids) != result.reason_ids
    ):
        raise ValueError("primary pipeline result reason ids invalid")
    return result


def _candidate_id_from_request(request: object) -> str | None:
    source = getattr(request, "worker_source", None)
    experience = getattr(source, "governed_experience_artifact", None)
    if not isinstance(experience, Mapping):
        return None
    candidate_id = experience.get("candidate_id")
    return candidate_id if type(candidate_id) is str else None


def _formation_with_candidate_identity(*args: Any, **kwargs: Any) -> Any:
    target = globals()["build_relaymem_primary_formation_dry_run"]
    if _CURRENT_CANDIDATE_ID is not None:
        kwargs["candidate_id"] = _CURRENT_CANDIDATE_ID
    return target(*args, **kwargs)


def _sync_helper_seams() -> None:
    _impl.build_relaymem_primary_formation_dry_run = (
        _formation_with_candidate_identity
    )
    for name in _HELPER_NAMES:
        setattr(_impl, name, globals()[name])


def _checkpoint_result(
    checkpoint: PrimaryPipelineCheckpoint,
    name: PrimaryPipelineCheckpointName,
) -> RelayMEMPrimaryPipelineCheckpointResult:
    try:
        value = checkpoint(name)
    except Exception:
        return RelayMEMPrimaryPipelineCheckpointResult(
            allowed=False,
            reason_ids=("primary_pipeline_checkpoint_callback_failed",),
        )
    if type(value) is not RelayMEMPrimaryPipelineCheckpointResult:
        return RelayMEMPrimaryPipelineCheckpointResult(
            allowed=False,
            reason_ids=("primary_pipeline_checkpoint_result_invalid",),
        )
    if type(value.allowed) is not bool or type(value.reason_ids) is not tuple:
        return RelayMEMPrimaryPipelineCheckpointResult(
            allowed=False,
            reason_ids=("primary_pipeline_checkpoint_result_invalid",),
        )
    reasons = _impl._reasons(value.reason_ids)
    if reasons != value.reason_ids:
        return RelayMEMPrimaryPipelineCheckpointResult(
            allowed=False,
            reason_ids=("primary_pipeline_checkpoint_result_invalid",),
        )
    if value.allowed and reasons:
        return RelayMEMPrimaryPipelineCheckpointResult(
            allowed=False,
            reason_ids=("primary_pipeline_checkpoint_result_invalid",),
        )
    if not value.allowed and not reasons:
        reasons = ("primary_pipeline_checkpoint_denied",)
    return RelayMEMPrimaryPipelineCheckpointResult(value.allowed, reasons)


def _checkpoint_denial(
    *,
    stage: str,
    checkpoint: PrimaryPipelineCheckpointName,
    decision: RelayMEMPrimaryPipelineCheckpointResult,
) -> RelayMEMPrimaryPipelineCheckpointDenied:
    reasons = _impl._reasons(
        decision.reason_ids or ("primary_pipeline_checkpoint_denied",)
    )
    return RelayMEMPrimaryPipelineCheckpointDenied(
        stage=stage,
        checkpoint=checkpoint,
        reason_ids=reasons or ("primary_pipeline_checkpoint_denied",),
    )


def _m3e_checkpoint_denied_result(
    denial: RelayMEMPrimaryPipelineCheckpointDenied,
) -> dict[str, Any]:
    reasons = list(denial.reason_ids)
    return {
        "schema_version": "relaymem.primary_page_write_apply.v0",
        "helper_only": True,
        "runtime_private_receipt": True,
        "enabled": True,
        "dry_run_only": False,
        "apply_enabled": True,
        "write_apply_supported": True,
        "apply_requested": True,
        "handoff_valid": False,
        "status": "blocked",
        "writes_memory": False,
        "page_applied": False,
        "idempotent_noop": False,
        "durability_confirmed": False,
        "cleanup_complete": False,
        "updates_index": False,
        "updates_log": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "runtime_wired": False,
        "visible_response_changed": False,
        "receipt": None,
        "blocked_reasons": reasons,
        "projection": {
            "schema_version": "relaymem.primary_page_write_projection.v0",
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "store_root_path_included": False,
            "candidate_id_included": False,
            "namespace_included": False,
            "target_path_included": False,
            "lineage_fingerprint_included": False,
            "idempotency_key_included": False,
            "page_markdown_included": False,
            "page_digest_included": False,
            "raw_source_text_included": False,
            "raw_message_history_included": False,
            "raw_affect_estimates_included": False,
            "status": "blocked",
            "handoff_valid": False,
            "target_category": "unknown",
            "memory_kind": "unknown",
            "page_bytes": 0,
            "writes_memory": False,
            "page_applied": False,
            "idempotent_noop": False,
            "durability_confirmed": False,
            "cleanup_complete": False,
            "updates_index": False,
            "updates_log": False,
            "blocked_reasons": reasons,
        },
    }


def _m3g_checkpoint_denied_result(
    denial: RelayMEMPrimaryPipelineCheckpointDenied,
) -> dict[str, Any]:
    reasons = list(denial.reason_ids)
    return {
        "schema_version": "relaymem.primary_index_log_reconciliation_apply.v0",
        "helper_only": True,
        "runtime_private_receipt": True,
        "enabled": True,
        "dry_run_only": False,
        "apply_enabled": True,
        "apply_supported": True,
        "apply_requested": True,
        "plan_valid": False,
        "page_verified": False,
        "status": "blocked",
        "writes_memory": False,
        "index_reconciled": False,
        "log_reconciled": False,
        "index_updated": False,
        "log_updated": False,
        "index_idempotent_noop": False,
        "log_idempotent_noop": False,
        "durability_confirmed": False,
        "cleanup_complete": False,
        "updates_index": False,
        "updates_log": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "runtime_wired": False,
        "lab_api_exposed": False,
        "visible_response_changed": False,
        "receipt": None,
        "blocked_reasons": reasons,
        "projection": {
            "schema_version": "relaymem.primary_index_log_reconciliation_apply_projection.v0",
            "diagnostics_only": True,
            "content_free": True,
            "content_included": False,
            "store_root_path_included": False,
            "target_paths_included": False,
            "namespace_included": False,
            "idempotency_key_included": False,
            "page_digest_included": False,
            "control_digests_included": False,
            "entry_identities_included": False,
            "proposed_content_included": False,
            "status": "blocked",
            "reconciliation_state": "unknown",
            "plan_valid": False,
            "page_verified": False,
            "apply_requested": True,
            "writes_memory": False,
            "index_reconciled": False,
            "log_reconciled": False,
            "index_updated": False,
            "log_updated": False,
            "idempotent_noop_count": 0,
            "durability_confirmed": False,
            "cleanup_complete": False,
            "conflict_count": 0,
            "blocked_reasons": reasons,
        },
    }


def execute_relaymem_primary_pipeline(
    request: object,
    *,
    checkpoint: PrimaryPipelineCheckpoint | None = None,
) -> RelayMEMPrimaryPipelineResult:
    """Execute compose with optional exact pre-side-effect checkpoints."""

    if checkpoint is not None and not callable(checkpoint):
        raise TypeError("checkpoint callable required")
    global _CURRENT_CANDIDATE_ID
    with _COMPOSE_LOCK:
        previous_candidate_id = _CURRENT_CANDIDATE_ID
        _CURRENT_CANDIDATE_ID = _candidate_id_from_request(request)
        try:
            _sync_helper_seams()
            if checkpoint is None:
                return _impl.execute_relaymem_primary_pipeline(request)

            original_consume = _impl.consume_relaymem_slp_primary_worker_source
            original_m3e = _impl.apply_relaymem_primary_page_write
            original_m3g = _impl.apply_relaymem_primary_index_log_reconciliation

            def consume_with_checkpoint(*args: Any, **kwargs: Any) -> Any:
                decision = _checkpoint_result(
                    checkpoint, "before_source_consumption"
                )
                if not decision.allowed:
                    return None, decision.reason_ids
                return original_consume(*args, **kwargs)

            def m3e_with_checkpoint(*args: Any, **kwargs: Any) -> Any:
                checkpoint_name = "before_m3e_page_writer"
                decision = _checkpoint_result(checkpoint, checkpoint_name)
                if not decision.allowed:
                    return _m3e_checkpoint_denied_result(
                        _checkpoint_denial(
                            stage="m3e_page_writer",
                            checkpoint=checkpoint_name,
                            decision=decision,
                        )
                    )
                return original_m3e(*args, **kwargs)

            def m3g_with_checkpoint(*args: Any, **kwargs: Any) -> Any:
                checkpoint_name = "before_m3g_reconciliation_apply"
                decision = _checkpoint_result(checkpoint, checkpoint_name)
                if not decision.allowed:
                    return _m3g_checkpoint_denied_result(
                        _checkpoint_denial(
                            stage="m3g_reconciliation_apply",
                            checkpoint=checkpoint_name,
                            decision=decision,
                        )
                    )
                return original_m3g(*args, **kwargs)

            _impl.consume_relaymem_slp_primary_worker_source = (
                consume_with_checkpoint
            )
            _impl.apply_relaymem_primary_page_write = m3e_with_checkpoint
            _impl.apply_relaymem_primary_index_log_reconciliation = (
                m3g_with_checkpoint
            )
            try:
                return _impl.execute_relaymem_primary_pipeline(request)
            finally:
                _impl.consume_relaymem_slp_primary_worker_source = original_consume
                _impl.apply_relaymem_primary_page_write = original_m3e
                _impl.apply_relaymem_primary_index_log_reconciliation = original_m3g
        finally:
            _CURRENT_CANDIDATE_ID = previous_candidate_id


def project_relaymem_primary_pipeline(
    result: RelayMEMPrimaryPipelineResult,
) -> RelayMEMPrimaryPipelineProjection:
    return _original_project(_validate_pipeline_result(result))


def build_relaymem_primary_pipeline_node_result(
    result: RelayMEMPrimaryPipelineResult,
) -> Any:
    _validate_pipeline_result(result)
    return _impl.build_relaymem_primary_pipeline_node_result(result)


# Runtime lookups inside result.to_log_dict() and the private node adapter must
# traverse the same strict public projection boundary.
_impl._validate_request = _validate_request
_impl.project_relaymem_primary_pipeline = project_relaymem_primary_pipeline


__all__ = [
    "PROJECTION_SCHEMA",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "STAGES",
    "PrimaryPipelineCheckpoint",
    "PrimaryPipelineCheckpointName",
    "RelayMEMPrimaryPipelineCheckpointDenied",
    "RelayMEMPrimaryPipelineCheckpointResult",
    "RelayMEMPrimaryPipelineProjection",
    "RelayMEMPrimaryPipelineRequest",
    "RelayMEMPrimaryPipelineResult",
    "RelayMEMPrimaryPipelineStageResult",
    "build_relaymem_primary_pipeline_node_result",
    "execute_relaymem_primary_pipeline",
    "project_relaymem_primary_pipeline",
]
