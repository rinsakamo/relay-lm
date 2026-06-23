"""Execution of one exact Phase 6-C1-2 already-claimed job."""
from __future__ import annotations

from .relaymem_primary_pipeline import (
    REQUEST_SCHEMA as PRIMARY_PIPELINE_REQUEST_SCHEMA,
    RelayMEMPrimaryPipelineRequest,
    RelayMEMPrimaryPipelineResult,
    execute_relaymem_primary_pipeline,
    project_relaymem_primary_pipeline,
)
from .relaymem_slp_primary_worker_outcome import (
    RelayMEMSLPPrimarySourceCorrelationOutcome,
    RelayMEMSLPPrimaryWorkerOutcome,
    classify_relaymem_slp_primary_worker_outcome,
)
from .relaymem_slp_primary_worker_source import validate_relaymem_slp_primary_worker_source
from ._relaymem_slp_primary_worker_fence import _CheckpointCoordinator, _check_active_claim
from ._relaymem_slp_primary_worker_outcome_adapter import (
    _apply_outcome_transition,
    _classify_pipeline,
    _side_effect_started,
)
from ._relaymem_slp_primary_worker_types import (
    RelayMEMSLPPrimaryWorkerRequest,
    RelayMEMSLPPrimaryWorkerResult,
    WorkerStatus,
)
from ._relaymem_slp_primary_worker_validate import (
    _finish_classified_without_pipeline,
    _result,
    _validate_request,
)

_CORRELATION_REASONS = frozenset({
    "worker_source_job_id_mismatch",
    "worker_source_dispatch_key_mismatch",
    "worker_source_run_id_mismatch",
    "worker_source_turn_index_mismatch",
    "worker_source_session_id_mismatch",
    "worker_source_namespace_mismatch",
    "worker_source_event_kind_mismatch",
    "worker_source_count_claim_mismatch",
    "worker_source_lineage_mismatch",
})


def execute_relaymem_slp_primary_worker(
    request: object,
) -> RelayMEMSLPPrimaryWorkerResult:
    """Execute one exact already-claimed Primary MEM job under B3 fences."""

    exact, request_reasons = _validate_request(request)
    if exact is None:
        return _result(
            status="invalid_input",
            request=request if type(request) is RelayMEMSLPPrimaryWorkerRequest else None,
            reasons=request_reasons,
        )
    if not exact.enabled:
        return _result(status="disabled", request=exact)

    initial_allowed, _, initial_reasons = _check_active_claim(
        exact.claimed_record,
        queue_root=exact.queue_root,
        lease_duration_seconds=exact.lease_duration_seconds,
        renew=False,
    )
    if not initial_allowed:
        return _result(
            status="lease_invalid_before_source",
            request=exact,
            reasons=initial_reasons,
        )

    source, source_reasons = validate_relaymem_slp_primary_worker_source(
        exact.worker_source,
        claimed_record=exact.claimed_record,
        request_scope=exact.request_scope,
    )
    if source is None:
        if (
            not exact.dry_run_only
            and source_reasons
            and all(reason in _CORRELATION_REASONS for reason in source_reasons)
        ):
            outcome = classify_relaymem_slp_primary_worker_outcome(
                m3e_result=None,
                m3g_result=None,
                m3h_result=None,
                source_correlation=RelayMEMSLPPrimarySourceCorrelationOutcome(
                    schema_version="relaymem.slp_primary_worker_source_correlation.v0",
                    status="invalid",
                ),
            )
            return _finish_classified_without_pipeline(
                exact, outcome, source_reasons
            )
        return _result(
            status="source_invalid",
            request=exact,
            initial_claim_valid=True,
            reasons=source_reasons,
        )
    assert source is exact.worker_source

    coordinator = _CheckpointCoordinator(exact)
    pipeline_request = RelayMEMPrimaryPipelineRequest(
        schema_version=PRIMARY_PIPELINE_REQUEST_SCHEMA,
        runtime_private=True,
        content_included=True,
        worker_source=source,
        claimed_record=dict(exact.claimed_record),
        request_scope=exact.request_scope,
        store_root=exact.store_root,
        enabled=True,
        dry_run_only=exact.dry_run_only,
        apply_enabled=exact.apply_enabled,
    )
    try:
        pipeline = execute_relaymem_primary_pipeline(
            pipeline_request, checkpoint=coordinator
        )
        project_relaymem_primary_pipeline(pipeline)
    except Exception:
        return _result(
            status="pipeline_blocked",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            reasons=("primary_worker_pipeline_execution_failed",),
        )

    if coordinator.denied_at is not None:
        status: WorkerStatus = {
            "before_source_consumption": "lease_invalid_before_source",
            "before_m3e_page_writer": "lease_lost_before_m3e",
            "before_m3g_reconciliation_apply": "lease_lost_before_m3g",
        }[coordinator.denied_at]
        return _result(
            status=status,
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            side_effect_started=_side_effect_started(pipeline),
            reasons=coordinator.reason_ids,
        )

    if exact.dry_run_only:
        status = "dry_run_ready" if pipeline.status == "dry_run_ready" else (
            "pipeline_held" if pipeline.status == "held" else "pipeline_blocked"
        )
        return _result(
            status=status,
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            side_effect_started=False,
            reasons=pipeline.reason_ids,
        )

    try:
        outcome = _classify_pipeline(pipeline)
    except Exception:
        return _result(
            status="pipeline_blocked",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            side_effect_started=_side_effect_started(pipeline),
            reasons=("primary_worker_outcome_classifier_failed",),
        )
    if type(outcome) is not RelayMEMSLPPrimaryWorkerOutcome:
        return _result(
            status="pipeline_blocked",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            side_effect_started=_side_effect_started(pipeline),
            reasons=("exact_primary_worker_outcome_required",),
        )
    if outcome.status != "classified" or outcome.transition_kind == "blocked_invalid_input":
        return _result(
            status="pipeline_blocked",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            outcome_result=outcome,
            side_effect_started=_side_effect_started(pipeline),
            reasons=(*pipeline.reason_ids, *outcome.blocked_reason_ids),
        )

    final_allowed, _, final_reasons = _check_active_claim(
        coordinator.current_record,
        queue_root=exact.queue_root,
        lease_duration_seconds=exact.lease_duration_seconds,
        renew=False,
    )
    if not final_allowed:
        return _result(
            status="lease_lost_before_transition",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            final_checkpoint_passed=False,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            outcome_result=outcome,
            side_effect_started=_side_effect_started(pipeline),
            reasons=final_reasons,
        )

    transition = _apply_outcome_transition(
        outcome,
        current_record=coordinator.current_record,
        queue_root=exact.queue_root,
        retry_not_before=exact.retry_not_before,
    )
    applied = (
        transition.status == "applied"
        and transition.transition_applied
        and transition.durability_confirmed
    )
    if not applied:
        return _result(
            status="transition_failed",
            request=exact,
            initial_claim_valid=True,
            source_checkpoint_passed=coordinator.source_checkpoint_passed,
            m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
            m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
            final_checkpoint_passed=True,
            lease_renewal_count=coordinator.lease_renewal_count,
            pipeline_result=pipeline,
            outcome_result=outcome,
            queue_transition_result=transition,
            side_effect_started=_side_effect_started(pipeline),
            reasons=transition.blocked_reasons or ("primary_worker_transition_failed",),
        )

    status = {
        "commit_succeeded": "terminal_succeeded",
        "retry_release": "retry_released",
        "commit_failed": "terminal_failed",
    }[outcome.transition_kind]
    return _result(
        status=status,
        request=exact,
        initial_claim_valid=True,
        source_checkpoint_passed=coordinator.source_checkpoint_passed,
        m3e_checkpoint_passed=coordinator.m3e_checkpoint_passed,
        m3g_checkpoint_passed=coordinator.m3g_checkpoint_passed,
        final_checkpoint_passed=True,
        lease_renewal_count=coordinator.lease_renewal_count,
        pipeline_result=pipeline,
        outcome_result=outcome,
        queue_transition_result=transition,
        side_effect_started=_side_effect_started(pipeline),
        queue_transition_performed=True,
        reasons=(),
    )


__all__ = [
    "execute_relaymem_slp_primary_worker",
    "execute_relaymem_primary_pipeline",
    "classify_relaymem_slp_primary_worker_outcome",
]
