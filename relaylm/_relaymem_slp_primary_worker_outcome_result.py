"""Outcome constructors and store-evidence mapping for Phase 6-C1."""
from __future__ import annotations

from ._relaymem_slp_primary_worker_outcome_types import (
    FailureClass,
    OutcomeStatus,
    RelayMEMSLPPrimaryReconciliationOutcome,
    RelayMEMSLPPrimaryRecoveryAuditOutcome,
    RelayMEMSLPPrimaryWorkerOutcome,
    RetryClass,
    TerminalState,
    TransitionKind,
)
from ._relaymem_slp_primary_worker_outcome_validate import dedupe


def success() -> RelayMEMSLPPrimaryWorkerOutcome:
    return outcome(
        status="classified",
        transition_kind="commit_succeeded",
        terminal_state="succeeded",
        retry_class="none",
        failure_class="none",
        terminal_reason_id="primary_mem_durable_state_verified",
        retryable=False,
        terminal=True,
        durable_success_verified=True,
    )


def retry(
    *, retry_class: RetryClass, failure_class: FailureClass
) -> RelayMEMSLPPrimaryWorkerOutcome:
    return outcome(
        status="classified",
        transition_kind="retry_release",
        terminal_state="",
        retry_class=retry_class,
        failure_class=failure_class,
        terminal_reason_id="",
        retryable=True,
        terminal=False,
    )


def terminal_failure(
    *,
    failure_class: FailureClass,
    reason_id: str,
    policy_held: bool = False,
    manual_confirmation_required: bool = False,
    recovery_isolation_required: bool = False,
) -> RelayMEMSLPPrimaryWorkerOutcome:
    return outcome(
        status="classified",
        transition_kind="commit_failed",
        terminal_state="failed",
        retry_class="none",
        failure_class=failure_class,
        terminal_reason_id=reason_id,
        retryable=False,
        terminal=True,
        policy_held=policy_held,
        manual_confirmation_required=manual_confirmation_required,
        recovery_isolation_required=recovery_isolation_required,
    )


def invalid(*reason_ids: str) -> RelayMEMSLPPrimaryWorkerOutcome:
    return outcome(
        status="invalid_input",
        transition_kind="blocked_invalid_input",
        terminal_state="",
        retry_class="none",
        failure_class="invalid_input",
        terminal_reason_id="primary_mem_worker_outcome_invalid_input",
        retryable=False,
        terminal=False,
        blocked_reason_ids=dedupe(reason_ids),
    )


def outcome(
    *,
    status: OutcomeStatus,
    transition_kind: TransitionKind,
    terminal_state: TerminalState,
    retry_class: RetryClass,
    failure_class: FailureClass,
    terminal_reason_id: str,
    retryable: bool,
    terminal: bool,
    policy_held: bool = False,
    manual_confirmation_required: bool = False,
    recovery_isolation_required: bool = False,
    durable_success_verified: bool = False,
    blocked_reason_ids: tuple[str, ...] = (),
) -> RelayMEMSLPPrimaryWorkerOutcome:
    return RelayMEMSLPPrimaryWorkerOutcome(
        status=status,
        transition_kind=transition_kind,
        terminal_state=terminal_state,
        retry_class=retry_class,
        failure_class=failure_class,
        terminal_reason_id=terminal_reason_id,
        retryable=retryable,
        terminal=terminal,
        policy_held=policy_held,
        manual_confirmation_required=manual_confirmation_required,
        recovery_isolation_required=recovery_isolation_required,
        durable_success_verified=durable_success_verified,
        blocked_reason_ids=blocked_reason_ids,
    )


def store_failure(
    m3g: RelayMEMSLPPrimaryReconciliationOutcome,
    m3h: RelayMEMSLPPrimaryRecoveryAuditOutcome | None,
) -> FailureClass | None:
    failure = store_failure_from_reasons(m3g.blocked_reason_ids)
    if failure is not None or m3h is None:
        return failure
    failure = store_failure_from_reasons(m3h.blocked_reason_ids)
    if failure is not None:
        return failure
    if m3h.store_state == "state_diverged":
        return "store_conflict"
    if m3h.store_state in {"page_unverified", "control_unverified"}:
        return "store_corruption"
    if m3h.index_state in {"diverged", "missing"} or (
        m3h.log_state in {"diverged", "missing"}
    ):
        return "store_conflict"
    if m3h.index_state == "invalid" or m3h.log_state == "invalid":
        return "store_corruption"
    return None


def store_failure_from_reasons(reason_ids: tuple[str, ...]) -> FailureClass | None:
    for reason in reason_ids:
        if reason.endswith("_page_missing") or "conflict" in reason:
            return "store_conflict"
        if "digest_mismatch" in reason or any(
            token in reason
            for token in (
                "_invalid",
                "_corrupt",
                "utf8",
                "symlink",
                "not_regular",
                "non_regular",
                "schema",
            )
        ):
            return "store_corruption"
    return None


def store_reason(failure_class: FailureClass) -> str:
    return (
        "primary_mem_store_conflict"
        if failure_class == "store_conflict"
        else "primary_mem_store_corruption"
    )
