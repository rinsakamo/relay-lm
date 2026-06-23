"""Strict content-free public view for the Phase 6-C1-2 worker."""
from __future__ import annotations

from .relaymem_primary_pipeline import (
    RelayMEMPrimaryPipelineResult,
    project_relaymem_primary_pipeline,
)
from .relaymem_slp_primary_worker_outcome import RelayMEMSLPPrimaryWorkerOutcome
from .relaymem_slp_queue_record import validate_record_mapping
from .relaymem_slp_queue_state import RelayMEMSLPQueueStateTransitionResult
from ._relaymem_slp_primary_worker_types import (
    RESULT_SCHEMA,
    RelayMEMSLPPrimaryWorkerProjection,
    RelayMEMSLPPrimaryWorkerResult,
)
from ._relaymem_slp_primary_worker_validate import _reason_ids

_STATUSES = frozenset(
    {
        "disabled",
        "dry_run_ready",
        "invalid_input",
        "lease_invalid_before_source",
        "source_invalid",
        "pipeline_blocked",
        "pipeline_held",
        "lease_lost_before_m3e",
        "lease_lost_before_m3g",
        "lease_lost_before_transition",
        "retry_released",
        "terminal_succeeded",
        "terminal_failed",
        "transition_failed",
    }
)
_CANONICAL_MODES = frozenset(
    {
        (False, True, False),
        (True, True, False),
        (True, False, True),
    }
)
_OUTCOME_STATUSES = frozenset({"classified", "invalid_input"})
_OUTCOME_KINDS = frozenset(
    {"commit_succeeded", "retry_release", "commit_failed", "blocked_invalid_input"}
)
_TERMINAL_STATES = frozenset({"", "succeeded", "failed"})
_RETRY_CLASSES = frozenset(
    {"none", "transient_lock_contention", "primary_reconciliation_retry"}
)
_FAILURE_CLASSES = frozenset(
    {
        "none",
        "resource_contention",
        "partial_progress_verified",
        "memory_policy_held",
        "memory_policy_blocked",
        "manual_confirmation_required",
        "recovery_isolation_required",
        "store_conflict",
        "store_corruption",
        "source_correlation_invalid",
        "invalid_input",
    }
)


def project_relaymem_slp_primary_worker(
    result: RelayMEMSLPPrimaryWorkerResult,
) -> RelayMEMSLPPrimaryWorkerProjection:
    """Validate an exact private result before producing a content-free view."""

    _validate_worker_result(result)
    pipeline_status = (
        result.pipeline_result.status
        if type(result.pipeline_result) is RelayMEMPrimaryPipelineResult
        else None
    )
    outcome_kind = (
        result.outcome_result.transition_kind
        if type(result.outcome_result) is RelayMEMSLPPrimaryWorkerOutcome
        else None
    )
    retryable = (
        result.status == "retry_released"
        or (
            type(result.outcome_result) is RelayMEMSLPPrimaryWorkerOutcome
            and result.outcome_result.retryable
        )
    )
    terminal = result.status in {"terminal_succeeded", "terminal_failed"}
    return RelayMEMSLPPrimaryWorkerProjection(
        status=result.status,
        enabled=result.enabled,
        dry_run_only=result.dry_run_only,
        apply_enabled=result.apply_enabled,
        initial_lease_valid=result.initial_claim_valid,
        source_checkpoint_passed=result.source_checkpoint_passed,
        m3e_checkpoint_passed=result.m3e_checkpoint_passed,
        m3g_checkpoint_passed=result.m3g_checkpoint_passed,
        final_checkpoint_passed=result.final_checkpoint_passed,
        lease_renewed=result.lease_renewal_count > 0,
        lease_renewal_count=result.lease_renewal_count,
        pipeline_status=pipeline_status,
        outcome_transition_kind=outcome_kind,
        queue_transition_performed=result.queue_transition_performed,
        retryable=retryable,
        terminal=terminal,
        succeeded=result.status == "terminal_succeeded",
        failed=result.status == "terminal_failed",
        reason_ids=result.reason_ids,
    )


def _validate_worker_result(result: object) -> RelayMEMSLPPrimaryWorkerResult:
    if type(result) is not RelayMEMSLPPrimaryWorkerResult:
        raise TypeError("exact RelayMEMSLPPrimaryWorkerResult required")
    if (
        result.schema_version != RESULT_SCHEMA
        or result.runtime_private is not True
        or result.content_included is not True
    ):
        raise ValueError("primary worker result envelope invalid")
    if result.status not in _STATUSES:
        raise ValueError("primary worker result status invalid")

    booleans = (
        result.enabled,
        result.dry_run_only,
        result.apply_enabled,
        result.initial_claim_valid,
        result.source_checkpoint_passed,
        result.m3e_checkpoint_passed,
        result.m3g_checkpoint_passed,
        result.final_checkpoint_passed,
        result.side_effect_started,
        result.queue_transition_performed,
    )
    if any(type(value) is not bool for value in booleans):
        raise ValueError("primary worker result boolean invalid")
    mode = (result.enabled, result.dry_run_only, result.apply_enabled)
    if mode not in _CANONICAL_MODES:
        raise ValueError("primary worker result gate mode invalid")
    if type(result.lease_renewal_count) is not int or result.lease_renewal_count < 0:
        raise ValueError("primary worker renewal count invalid")
    if type(result.reason_ids) is not tuple or _reason_ids(result.reason_ids) != result.reason_ids:
        raise ValueError("primary worker result reason ids invalid")

    pipeline = result.pipeline_result
    if pipeline is not None:
        if type(pipeline) is not RelayMEMPrimaryPipelineResult:
            raise ValueError("exact primary pipeline result required")
        project_relaymem_primary_pipeline(pipeline)
    outcome = result.outcome_result
    if outcome is not None:
        _validate_outcome(outcome)
    queue = result.queue_transition_result
    if queue is not None:
        _validate_queue_result(queue)

    if result.m3g_checkpoint_passed and not result.m3e_checkpoint_passed:
        raise ValueError("primary worker checkpoint order invalid")
    if result.m3e_checkpoint_passed and not result.source_checkpoint_passed:
        raise ValueError("primary worker checkpoint order invalid")
    if (result.m3e_checkpoint_passed or result.m3g_checkpoint_passed) and mode != (
        True,
        False,
        True,
    ):
        raise ValueError("primary worker apply checkpoint mode invalid")
    if result.lease_renewal_count > 0 and (
        mode != (True, False, True) or not result.source_checkpoint_passed
    ):
        raise ValueError("primary worker renewal ledger invalid")
    if result.queue_transition_performed and not result.final_checkpoint_passed:
        raise ValueError("primary worker stale transition ledger invalid")
    if result.final_checkpoint_passed != (queue is not None):
        raise ValueError("primary worker final checkpoint ledger invalid")

    expected_side_effect = bool(
        type(pipeline) is RelayMEMPrimaryPipelineResult
        and pipeline.m3e_result is not None
    )
    if result.side_effect_started is not expected_side_effect:
        raise ValueError("primary worker side effect ledger invalid")

    if result.status == "disabled":
        if mode != (False, True, False) or any(
            (
                result.initial_claim_valid,
                result.source_checkpoint_passed,
                result.m3e_checkpoint_passed,
                result.m3g_checkpoint_passed,
                result.final_checkpoint_passed,
                result.side_effect_started,
                result.queue_transition_performed,
                result.lease_renewal_count,
                pipeline is not None,
                outcome is not None,
                queue is not None,
            )
        ):
            raise ValueError("primary worker disabled ledger invalid")
    elif not result.enabled and result.status != "invalid_input":
        raise ValueError("primary worker disabled status invalid")

    if result.dry_run_only and (
        result.lease_renewal_count
        or result.side_effect_started
        or result.final_checkpoint_passed
        or result.queue_transition_performed
        or outcome is not None
        or queue is not None
    ):
        raise ValueError("primary worker dry-run mutation ledger invalid")
    if result.status == "dry_run_ready" and (
        mode != (True, True, False)
        or type(pipeline) is not RelayMEMPrimaryPipelineResult
        or pipeline.status != "dry_run_ready"
    ):
        raise ValueError("primary worker dry-run status invalid")

    terminal_kinds = {
        "terminal_succeeded": "commit_succeeded",
        "terminal_failed": "commit_failed",
        "retry_released": "retry_release",
    }
    if result.status in terminal_kinds:
        expected_kind = terminal_kinds[result.status]
        if (
            type(outcome) is not RelayMEMSLPPrimaryWorkerOutcome
            or outcome.transition_kind != expected_kind
            or type(queue) is not RelayMEMSLPQueueStateTransitionResult
            or not result.queue_transition_performed
            or queue.status != "applied"
            or queue.transition_kind
            != ("retry_release" if expected_kind == "retry_release" else "commit_terminal")
            or queue.transition_applied is not True
            or queue.durability_confirmed is not True
        ):
            raise ValueError("primary worker completed transition ledger invalid")
    elif result.queue_transition_performed:
        raise ValueError("primary worker unexpected queue transition")

    if result.status == "transition_failed" and (
        type(outcome) is not RelayMEMSLPPrimaryWorkerOutcome
        or type(queue) is not RelayMEMSLPQueueStateTransitionResult
        or result.final_checkpoint_passed is not True
        or queue.transition_applied is not False
    ):
        raise ValueError("primary worker failed transition ledger invalid")
    if result.status == "lease_lost_before_transition" and (
        outcome is None
        or result.final_checkpoint_passed
        or queue is not None
        or result.queue_transition_performed
    ):
        raise ValueError("primary worker lost lease ledger invalid")
    return result


def _validate_outcome(value: object) -> RelayMEMSLPPrimaryWorkerOutcome:
    if type(value) is not RelayMEMSLPPrimaryWorkerOutcome:
        raise ValueError("exact primary worker outcome required")
    if (
        value.status not in _OUTCOME_STATUSES
        or value.transition_kind not in _OUTCOME_KINDS
        or value.terminal_state not in _TERMINAL_STATES
        or value.retry_class not in _RETRY_CLASSES
        or value.failure_class not in _FAILURE_CLASSES
        or type(value.terminal_reason_id) is not str
        or type(value.blocked_reason_ids) is not tuple
        or _reason_ids(value.blocked_reason_ids) != value.blocked_reason_ids
    ):
        raise ValueError("primary worker outcome invalid")
    if any(
        type(item) is not bool
        for item in (
            value.retryable,
            value.terminal,
            value.policy_held,
            value.manual_confirmation_required,
            value.recovery_isolation_required,
            value.durable_success_verified,
        )
    ):
        raise ValueError("primary worker outcome boolean invalid")
    if value.transition_kind == "commit_succeeded" and not (
        value.status == "classified"
        and value.terminal_state == "succeeded"
        and value.retry_class == "none"
        and value.failure_class == "none"
        and value.terminal_reason_id == "primary_mem_durable_state_verified"
        and value.retryable is False
        and value.terminal is True
        and value.durable_success_verified is True
    ):
        raise ValueError("primary worker success outcome invalid")
    if value.transition_kind == "retry_release" and not (
        value.status == "classified"
        and value.terminal_state == ""
        and value.retry_class
        in {"transient_lock_contention", "primary_reconciliation_retry"}
        and value.failure_class
        in {"resource_contention", "partial_progress_verified"}
        and value.terminal_reason_id == ""
        and value.retryable is True
        and value.terminal is False
        and value.durable_success_verified is False
    ):
        raise ValueError("primary worker retry outcome invalid")
    if value.transition_kind == "commit_failed" and not (
        value.status == "classified"
        and value.terminal_state == "failed"
        and value.retry_class == "none"
        and value.failure_class not in {"none", "invalid_input"}
        and bool(value.terminal_reason_id)
        and value.retryable is False
        and value.terminal is True
        and value.durable_success_verified is False
    ):
        raise ValueError("primary worker failed outcome invalid")
    if value.transition_kind == "blocked_invalid_input" and not (
        value.status == "invalid_input"
        and value.terminal_state == ""
        and value.retry_class == "none"
        and value.failure_class == "invalid_input"
        and value.terminal_reason_id == ""
        and value.retryable is False
        and value.terminal is False
        and value.durable_success_verified is False
    ):
        raise ValueError("primary worker invalid outcome invalid")
    return value


def _validate_queue_result(
    value: object,
) -> RelayMEMSLPQueueStateTransitionResult:
    if type(value) is not RelayMEMSLPQueueStateTransitionResult:
        raise ValueError("exact B3 transition result required")
    if any(
        type(item) is not bool
        for item in (
            value.enabled,
            value.dry_run_only,
            value.apply_enabled,
            value.queue_io_performed,
            value.transition_attempted,
            value.transition_applied,
            value.durability_confirmed,
        )
    ):
        raise ValueError("B3 transition result boolean invalid")
    if type(value.blocked_reasons) is not tuple or _reason_ids(
        value.blocked_reasons
    ) != value.blocked_reasons:
        raise ValueError("B3 transition result reasons invalid")
    if value.durable_record is not None and (
        type(value.durable_record) is not dict
        or validate_record_mapping(value.durable_record)
    ):
        raise ValueError("B3 transition durable record invalid")
    return value


__all__ = ["project_relaymem_slp_primary_worker"]
