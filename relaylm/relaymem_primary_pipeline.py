"""Public RelayMEM Phase 6-C1-1 Primary MEM pipeline boundary.

The implementation remains runtime-private in the adjacent implementation
module. This facade fixes the exact public types, synchronizes testable M3
helper seams, and rejects non-canonical request modes or impossible result
ledgers before any public projection is produced.
"""
from __future__ import annotations

from typing import Any

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
    "build_relaymem_primary_formation_dry_run",
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
    if (result.enabled, result.dry_run_only, result.apply_enabled) not in _CANONICAL_MODES:
        raise ValueError("primary pipeline result gate mode invalid")
    if result.status not in _PIPELINE_STATUSES:
        raise ValueError("primary pipeline result status invalid")
    if type(result.stage_results) is not tuple or len(result.stage_results) != len(STAGES):
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
        if type(item.reason_ids) is not tuple or _impl._reasons(item.reason_ids) != item.reason_ids:
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
        if item.status == "completed" and (not item.executed or not item.completed):
            raise ValueError("primary pipeline completed stage flags invalid")
        if item.status == "blocked" and (not item.executed or not item.blocked):
            raise ValueError("primary pipeline blocked stage flags invalid")
        if item.status == "held" and (not item.executed or not item.held):
            raise ValueError("primary pipeline held stage flags invalid")
        if item.status == "retryable" and (not item.executed or not item.retryable):
            raise ValueError("primary pipeline retryable stage flags invalid")
        if item.executed:
            executed_indexes.append(index)
        if item.completed:
            completed_indexes.append(index)

    if executed_indexes and executed_indexes != list(range(executed_indexes[-1] + 1)):
        raise ValueError("primary pipeline executed stage order invalid")
    if completed_indexes and completed_indexes != list(range(completed_indexes[-1] + 1)):
        raise ValueError("primary pipeline completed stage order invalid")
    if type(result.completed_stage_count) is not int or (
        result.completed_stage_count != len(completed_indexes)
    ):
        raise ValueError("primary pipeline completed stage count invalid")

    expected_last = STAGES[executed_indexes[-1]] if executed_indexes else None
    expected_completed = STAGES[completed_indexes[-1]] if completed_indexes else None
    if result.last_stage != expected_last:
        raise ValueError("primary pipeline last stage invalid")
    if result.last_completed_stage != expected_completed:
        raise ValueError("primary pipeline last completed stage invalid")
    if type(result.reason_ids) is not tuple or _impl._reasons(result.reason_ids) != result.reason_ids:
        raise ValueError("primary pipeline result reason ids invalid")
    return result


def _sync_helper_seams() -> None:
    for name in _HELPER_NAMES:
        setattr(_impl, name, globals()[name])


def execute_relaymem_primary_pipeline(
    request: object,
) -> RelayMEMPrimaryPipelineResult:
    _sync_helper_seams()
    return _impl.execute_relaymem_primary_pipeline(request)


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
    "RelayMEMPrimaryPipelineProjection",
    "RelayMEMPrimaryPipelineRequest",
    "RelayMEMPrimaryPipelineResult",
    "RelayMEMPrimaryPipelineStageResult",
    "build_relaymem_primary_pipeline_node_result",
    "execute_relaymem_primary_pipeline",
    "project_relaymem_primary_pipeline",
]
