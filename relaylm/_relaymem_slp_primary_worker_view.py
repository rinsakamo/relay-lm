"""Content-free public view for the Phase 6-C1-2 worker."""
from __future__ import annotations

from .relaymem_primary_pipeline import RelayMEMPrimaryPipelineResult
from .relaymem_slp_primary_worker_outcome import RelayMEMSLPPrimaryWorkerOutcome
from ._relaymem_slp_primary_worker_types import (
    RESULT_SCHEMA,
    RelayMEMSLPPrimaryWorkerProjection,
    RelayMEMSLPPrimaryWorkerResult,
)


def project_relaymem_slp_primary_worker(
    result: RelayMEMSLPPrimaryWorkerResult,
) -> RelayMEMSLPPrimaryWorkerProjection:
    if type(result) is not RelayMEMSLPPrimaryWorkerResult:
        raise TypeError("exact RelayMEMSLPPrimaryWorkerResult required")
    if (
        result.schema_version != RESULT_SCHEMA
        or result.runtime_private is not True
        or result.content_included is not True
    ):
        raise ValueError("primary worker result envelope invalid")
    if type(result.lease_renewal_count) is not int or result.lease_renewal_count < 0:
        raise ValueError("primary worker renewal count invalid")
    for value in (
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
    ):
        if type(value) is not bool:
            raise ValueError("primary worker result boolean invalid")
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


__all__ = ["project_relaymem_slp_primary_worker"]
