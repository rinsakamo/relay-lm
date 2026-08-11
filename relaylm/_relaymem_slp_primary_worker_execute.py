"""Execution of one exact Phase 6-C1-2 already-claimed job."""
from __future__ import annotations

from .relaymem_primary_pipeline import execute_relaymem_primary_pipeline
from .relaymem_slp_primary_worker_outcome import (
    RelayMEMSLPPrimarySourceCorrelationOutcome,
    RelayMEMSLPPrimaryWorkerOutcome,
    classify_relaymem_slp_primary_worker_outcome,
)
from .relaymem_slp_primary_worker_source import validate_relaymem_slp_primary_worker_source
from ._relaymem_slp_primary_worker_fence import _check_active_claim
from ._relaymem_slp_primary_worker_pipeline import (
    _PrimaryWorkerPipelineExecution,
    _execute_primary_worker_pipeline,
)
from ._relaymem_slp_primary_worker_outcome_adapter import (
    _apply_outcome_transition,
    _bounded_outcome_and_retry,
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
from .subjective_mem.retrieval_cutover import primary_writer_decision_permits_write

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
    if not primary_writer_decision_permits_write(exact.primary_writer_decision):
        return _result(
            status="invalid_input",
            request=exact,
            reasons=("primary_writer_decision_rejected",),
        )
    if not exact.enabled:
        return _result(status="disabled", request=exact)
    source_or_result = _validate_claim_and_source(exact)
    if type(source_or_result) is RelayMEMSLPPrimaryWorkerResult:
        return source_or_result
    execution = _execute_primary_worker_pipeline(
        exact,
        source_or_result,
        execute_pipeline=execute_relaymem_primary_pipeline,
    )
    return _finish_pipeline_execution(exact, execution)


def _validate_claim_and_source(request: RelayMEMSLPPrimaryWorkerRequest) -> object:
    allowed, _, reasons = _check_active_claim(
        request.claimed_record,
        queue_root=request.queue_root,
        lease_duration_seconds=request.lease_duration_seconds,
        renew=False,
    )
    if not allowed:
        return _result(status="lease_invalid_before_source", request=request, reasons=reasons)
    source, reasons = validate_relaymem_slp_primary_worker_source(
        request.worker_source,
        claimed_record=request.claimed_record,
        request_scope=request.request_scope,
    )
    if source is not None:
        return source
    if not request.dry_run_only and reasons and all(
        reason in _CORRELATION_REASONS for reason in reasons
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
        return _finish_classified_without_pipeline(request, outcome, reasons)
    return _result(
        status="source_invalid",
        request=request,
        initial_claim_valid=True,
        reasons=reasons,
    )


def _pipeline_result_fields(execution: _PrimaryWorkerPipelineExecution) -> dict[str, object]:
    coordinator = execution.coordinator
    return {
        "initial_claim_valid": True,
        "source_checkpoint_passed": coordinator.source_checkpoint_passed,
        "m3e_checkpoint_passed": coordinator.m3e_checkpoint_passed,
        "m3g_checkpoint_passed": coordinator.m3g_checkpoint_passed,
        "lease_renewal_count": coordinator.lease_renewal_count,
    }


def _finish_pipeline_execution(
    request: RelayMEMSLPPrimaryWorkerRequest,
    execution: _PrimaryWorkerPipelineExecution,
) -> RelayMEMSLPPrimaryWorkerResult:
    fields = _pipeline_result_fields(execution)
    if execution.execution_failed:
        return _result(
            status="pipeline_blocked",
            request=request,
            reasons=("primary_worker_pipeline_execution_failed",),
            **fields,
        )
    pipeline = execution.pipeline_result
    assert pipeline is not None
    if execution.coordinator.denied_at is not None:
        return _finish_checkpoint_denial(request, execution)
    if request.dry_run_only:
        status: WorkerStatus = {
            "dry_run_ready": "dry_run_ready",
            "held": "pipeline_held",
        }.get(pipeline.status, "pipeline_blocked")
        return _result(
            status=status,
            request=request,
            pipeline_result=pipeline,
            side_effect_started=False,
            reasons=pipeline.reason_ids,
            **fields,
        )
    return _classify_and_transition(request, execution)


def _finish_checkpoint_denial(
    request: RelayMEMSLPPrimaryWorkerRequest,
    execution: _PrimaryWorkerPipelineExecution,
) -> RelayMEMSLPPrimaryWorkerResult:
    coordinator = execution.coordinator
    status: WorkerStatus = {
        "before_source_consumption": "lease_invalid_before_source",
        "before_m3e_page_writer": "lease_lost_before_m3e",
        "before_m3g_reconciliation_apply": "lease_lost_before_m3g",
    }[coordinator.denied_at]  # type: ignore[index]
    pipeline = execution.pipeline_result
    assert pipeline is not None
    return _result(
        status=status,
        request=request,
        pipeline_result=pipeline,
        side_effect_started=_side_effect_started(pipeline),
        reasons=coordinator.reason_ids,
        **_pipeline_result_fields(execution),
    )


def _classify_and_transition(
    request: RelayMEMSLPPrimaryWorkerRequest,
    execution: _PrimaryWorkerPipelineExecution,
) -> RelayMEMSLPPrimaryWorkerResult:
    pipeline = execution.pipeline_result
    assert pipeline is not None
    try:
        outcome = _classify_pipeline(pipeline)
    except Exception:
        return _blocked_classification(request, execution, None)
    if type(outcome) is not RelayMEMSLPPrimaryWorkerOutcome:
        return _blocked_classification(request, execution, None, exact_required=True)
    if outcome.status != "classified" or outcome.transition_kind == "blocked_invalid_input":
        return _blocked_classification(request, execution, outcome)
    return _apply_classified_transition(request, execution, outcome)


def _blocked_classification(
    request: RelayMEMSLPPrimaryWorkerRequest,
    execution: _PrimaryWorkerPipelineExecution,
    outcome: RelayMEMSLPPrimaryWorkerOutcome | None,
    *,
    exact_required: bool = False,
) -> RelayMEMSLPPrimaryWorkerResult:
    pipeline = execution.pipeline_result
    assert pipeline is not None
    if exact_required:
        reasons = ("exact_primary_worker_outcome_required",)
    elif outcome is None:
        reasons = ("primary_worker_outcome_classifier_failed",)
    else:
        reasons = (*pipeline.reason_ids, *outcome.blocked_reason_ids)
    return _result(
        status="pipeline_blocked",
        request=request,
        pipeline_result=pipeline,
        outcome_result=outcome,
        side_effect_started=_side_effect_started(pipeline),
        reasons=reasons,
        **_pipeline_result_fields(execution),
    )


def _apply_classified_transition(
    request: RelayMEMSLPPrimaryWorkerRequest,
    execution: _PrimaryWorkerPipelineExecution,
    outcome: RelayMEMSLPPrimaryWorkerOutcome,
) -> RelayMEMSLPPrimaryWorkerResult:
    coordinator = execution.coordinator
    pipeline = execution.pipeline_result
    assert pipeline is not None
    outcome, retry_at = _bounded_outcome_and_retry(outcome, coordinator.current_record)
    allowed, _, reasons = _check_active_claim(
        coordinator.current_record,
        queue_root=request.queue_root,
        lease_duration_seconds=request.lease_duration_seconds,
        renew=False,
    )
    if not allowed:
        return _transition_result(
            "lease_lost_before_transition", request, execution, outcome, reasons=reasons
        )
    transition = _apply_outcome_transition(
        outcome,
        current_record=coordinator.current_record,
        queue_root=request.queue_root,
        retry_not_before=retry_at,
    )
    if not (
        transition.status == "applied"
        and transition.transition_applied
        and transition.durability_confirmed
    ):
        return _transition_result(
            "transition_failed",
            request,
            execution,
            outcome,
            transition=transition,
            reasons=transition.blocked_reasons or ("primary_worker_transition_failed",),
        )
    status: WorkerStatus = {
        "commit_succeeded": "terminal_succeeded",
        "retry_release": "retry_released",
        "commit_failed": "terminal_failed",
    }[outcome.transition_kind]
    return _transition_result(
        status, request, execution, outcome, transition=transition, performed=True
    )


def _transition_result(
    status: WorkerStatus,
    request: RelayMEMSLPPrimaryWorkerRequest,
    execution: _PrimaryWorkerPipelineExecution,
    outcome: RelayMEMSLPPrimaryWorkerOutcome,
    *,
    transition: object = None,
    performed: bool = False,
    reasons: tuple[str, ...] = (),
) -> RelayMEMSLPPrimaryWorkerResult:
    pipeline = execution.pipeline_result
    assert pipeline is not None
    return _result(
        status=status,
        request=request,
        final_checkpoint_passed=status != "lease_lost_before_transition",
        pipeline_result=pipeline,
        outcome_result=outcome,
        queue_transition_result=transition,
        side_effect_started=_side_effect_started(pipeline),
        queue_transition_performed=performed,
        reasons=reasons,
        **_pipeline_result_fields(execution),
    )


__all__ = [
    "execute_relaymem_slp_primary_worker",
    "execute_relaymem_primary_pipeline",
    "classify_relaymem_slp_primary_worker_outcome",
]
