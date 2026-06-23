"""Pure classification logic for Phase 6-C1 Primary MEM worker outcomes."""
from __future__ import annotations

from ._relaymem_slp_primary_worker_outcome_result import (
    invalid,
    retry,
    store_failure,
    store_failure_from_reasons,
    store_reason,
    success,
    terminal_failure,
)
from ._relaymem_slp_primary_worker_outcome_types import (
    RelayMEMSLPPrimaryPageWriteOutcome,
    RelayMEMSLPPrimaryPolicyOutcome,
    RelayMEMSLPPrimaryReconciliationOutcome,
    RelayMEMSLPPrimaryRecoveryAuditOutcome,
    RelayMEMSLPPrimarySourceCorrelationOutcome,
    RelayMEMSLPPrimaryWorkerOutcome,
)
from ._relaymem_slp_primary_worker_outcome_validate import (
    M3E_UNCERTAIN,
    M3G_LOCK_REASON,
    M3G_UNCERTAIN,
    M3H_LOCK_REASON,
    validate_inputs,
)


def classify_relaymem_slp_primary_worker_outcome(
    *,
    m3e_result: object | None,
    m3g_result: object | None,
    m3h_result: object | None,
    policy_outcome: object | None = None,
    source_correlation: object | None = None,
) -> RelayMEMSLPPrimaryWorkerOutcome:
    """Map exact RelayMEM meanings to a pure Phase 6-B3 transition intent."""

    errors = validate_inputs(
        m3e_result=m3e_result,
        m3g_result=m3g_result,
        m3h_result=m3h_result,
        policy_outcome=policy_outcome,
        source_correlation=source_correlation,
    )
    if errors:
        return invalid(*errors)

    m3e = _exact(m3e_result, RelayMEMSLPPrimaryPageWriteOutcome)
    m3g = _exact(m3g_result, RelayMEMSLPPrimaryReconciliationOutcome)
    m3h = _exact(m3h_result, RelayMEMSLPPrimaryRecoveryAuditOutcome)
    policy = _exact(policy_outcome, RelayMEMSLPPrimaryPolicyOutcome)
    correlation = _exact(
        source_correlation, RelayMEMSLPPrimarySourceCorrelationOutcome
    )

    if correlation is not None and correlation.status == "invalid":
        if any(item is not None for item in (m3e, m3g, m3h, policy)):
            return invalid("source_correlation_result_combination_invalid")
        return terminal_failure(
            failure_class="source_correlation_invalid",
            reason_id="primary_mem_source_correlation_invalid",
        )

    if policy is not None:
        if any(item is not None for item in (m3e, m3g, m3h)):
            return invalid("policy_result_combination_invalid")
        return terminal_failure(
            failure_class=(
                "memory_policy_held"
                if policy.status == "held"
                else "memory_policy_blocked"
            ),
            reason_id=policy.reason_id,
            policy_held=True,
        )

    if m3e is None or m3g is None:
        return invalid("m3e_m3g_results_required")

    if not _m3e_page_exact(m3e) and m3e.status not in M3E_UNCERTAIN:
        failure = store_failure_from_reasons(m3e.blocked_reason_ids)
        if failure is not None:
            return terminal_failure(
                failure_class=failure, reason_id=store_reason(failure)
            )
        return invalid("m3e_page_state_not_exact")

    if M3G_LOCK_REASON in m3g.blocked_reason_ids:
        if m3h is not None:
            return invalid("m3g_lock_with_m3h_result_invalid")
        return retry(
            retry_class="transient_lock_contention",
            failure_class="resource_contention",
        )

    if m3h is not None and m3h.source_status != m3g.status:
        return invalid("m3g_m3h_source_status_mismatch")

    if m3h is not None and M3H_LOCK_REASON in m3h.blocked_reason_ids:
        if not _m3h_lock_contention_is_clean(m3h):
            return invalid("m3h_lock_with_invalid_store_evidence")
        return retry(
            retry_class="transient_lock_contention",
            failure_class="resource_contention",
        )

    if m3g.status in M3G_UNCERTAIN:
        return _classify_uncertainty(m3h)

    if m3e.status in M3E_UNCERTAIN:
        return _classify_page_uncertainty(m3e, m3h)

    failure = store_failure(m3g, m3h)
    if failure is not None:
        return terminal_failure(
            failure_class=failure, reason_id=store_reason(failure)
        )

    if m3h is not None and (
        m3h.recovery_classification == "manual_confirmation_required"
    ):
        return _manual()
    if m3h is not None and (
        m3h.recovery_classification == "journaled_recovery_candidate"
    ):
        return _isolate()

    if _verified_partial(m3g, m3h):
        return retry(
            retry_class="primary_reconciliation_retry",
            failure_class="partial_progress_verified",
        )

    if m3g.status in {"applied", "already_applied"}:
        if m3h is None:
            return invalid("m3h_required_for_terminal_success")
        if not _m3h_durable_success(m3h):
            return invalid("terminal_success_evidence_incomplete")
        return success()

    if m3h is not None and (
        m3h.recovery_classification == "recovery_not_required"
    ):
        return invalid("m3g_not_applied_with_recovery_not_required")
    return invalid("incompatible_m3_result_combination")


def _m3h_lock_contention_is_clean(
    value: RelayMEMSLPPrimaryRecoveryAuditOutcome,
) -> bool:
    return (
        value.status == "blocked"
        and value.receipt_valid
        and value.store_state == "not_evaluated"
        and not value.page_verified
        and value.index_state == "not_checked"
        and value.log_state == "not_checked"
        and not value.cleanup_artifacts_present
        and value.recovery_classification == "not_evaluated"
        and value.blocked_reason_ids == (M3H_LOCK_REASON,)
    )


def _classify_uncertainty(
    m3h: RelayMEMSLPPrimaryRecoveryAuditOutcome | None,
) -> RelayMEMSLPPrimaryWorkerOutcome:
    if m3h is None:
        return invalid("m3h_required_for_m3g_durability_uncertainty")
    if (
        m3h.store_state == "index_applied_log_pending"
        and m3h.recovery_classification == "retry_reconciliation"
        and m3h.page_verified
    ):
        return retry(
            retry_class="primary_reconciliation_retry",
            failure_class="partial_progress_verified",
        )
    if m3h.recovery_classification == "manual_confirmation_required":
        return _manual()
    if m3h.recovery_classification == "journaled_recovery_candidate":
        return _isolate()
    return invalid("m3g_durability_uncertainty_unclassified")


def _classify_page_uncertainty(
    m3e: RelayMEMSLPPrimaryPageWriteOutcome,
    m3h: RelayMEMSLPPrimaryRecoveryAuditOutcome | None,
) -> RelayMEMSLPPrimaryWorkerOutcome:
    if m3h is not None:
        if m3h.recovery_classification == "manual_confirmation_required":
            return _manual()
        if m3h.recovery_classification == "journaled_recovery_candidate":
            return _isolate()
    if m3e.status == "applied_durability_unconfirmed":
        return _manual()
    return _isolate()


def _verified_partial(m3g, m3h) -> bool:
    return (
        m3g.status == "index_applied_log_pending"
        and m3h is not None
        and m3h.store_state == "index_applied_log_pending"
        and m3h.recovery_classification == "retry_reconciliation"
        and m3h.page_verified
    )


def _m3e_page_exact(value) -> bool:
    return value.status in {"applied", "already_applied"} and value.page_applied


def _m3h_durable_success(value) -> bool:
    return (
        value.status == "recovery_not_required"
        and value.receipt_valid
        and value.store_state == "fully_reconciled"
        and value.page_verified
        and value.index_state == "proposed"
        and value.log_state == "proposed"
        and not value.cleanup_artifacts_present
        and value.recovery_classification == "recovery_not_required"
        and not value.blocked_reason_ids
    )


def _manual() -> RelayMEMSLPPrimaryWorkerOutcome:
    return terminal_failure(
        failure_class="manual_confirmation_required",
        reason_id="primary_mem_manual_confirmation_required",
        manual_confirmation_required=True,
    )


def _isolate() -> RelayMEMSLPPrimaryWorkerOutcome:
    return terminal_failure(
        failure_class="recovery_isolation_required",
        reason_id="primary_mem_journaled_recovery_candidate",
        recovery_isolation_required=True,
    )


def _exact(value, expected_type):
    return value if type(value) is expected_type else None
