"""Fixtures for the Phase 6-C1 Primary MEM worker outcome smoke."""
from __future__ import annotations

from relaylm.relaymem_slp_primary_worker_outcome import (
    RelayMEMSLPPrimaryPageWriteOutcome,
    RelayMEMSLPPrimaryPolicyOutcome,
    RelayMEMSLPPrimaryReconciliationOutcome,
    RelayMEMSLPPrimaryRecoveryAuditOutcome,
    RelayMEMSLPPrimaryWorkerOutcome,
    classify_relaymem_slp_primary_worker_outcome,
)

M3E_SCHEMA = "relaymem.primary_page_write_apply.v0"
M3G_SCHEMA = "relaymem.primary_index_log_reconciliation_apply.v0"
M3H_SCHEMA = "relaymem.primary_index_log_reconciliation_recovery_audit_result.v0"
POLICY_SCHEMA = "relaymem.slp_primary_worker_policy_outcome.v0"


def m3e_applied() -> RelayMEMSLPPrimaryPageWriteOutcome:
    return RelayMEMSLPPrimaryPageWriteOutcome(
        M3E_SCHEMA, "applied", True, True, True, False, True, True
    )


def m3e_idempotent() -> RelayMEMSLPPrimaryPageWriteOutcome:
    return RelayMEMSLPPrimaryPageWriteOutcome(
        M3E_SCHEMA, "already_applied", True, False, True, True, False, True
    )


def m3g(
    status: str = "applied", *, reasons: tuple[str, ...] = ()
) -> RelayMEMSLPPrimaryReconciliationOutcome:
    common = dict(schema_version=M3G_SCHEMA, status=status, plan_valid=True)
    if status == "already_applied":
        return RelayMEMSLPPrimaryReconciliationOutcome(
            **common,
            page_verified=True,
            writes_memory=False,
            index_reconciled=True,
            log_reconciled=True,
            index_updated=False,
            log_updated=False,
            index_idempotent_noop=True,
            log_idempotent_noop=True,
            durability_confirmed=True,
            cleanup_complete=True,
            blocked_reason_ids=reasons,
        )
    if status == "index_applied_log_pending":
        return RelayMEMSLPPrimaryReconciliationOutcome(
            **common,
            page_verified=True,
            writes_memory=True,
            index_reconciled=True,
            log_reconciled=False,
            index_updated=True,
            log_updated=False,
            index_idempotent_noop=False,
            log_idempotent_noop=False,
            durability_confirmed=False,
            cleanup_complete=True,
            blocked_reason_ids=reasons,
        )
    if status in {
        "applied_durability_unconfirmed",
        "applied_cleanup_incomplete",
        "applied_state_uncertain",
    }:
        return RelayMEMSLPPrimaryReconciliationOutcome(
            **common,
            page_verified=True,
            writes_memory=True,
            index_reconciled=status != "applied_state_uncertain",
            log_reconciled=status == "applied_durability_unconfirmed",
            index_updated=True,
            log_updated=True,
            index_idempotent_noop=False,
            log_idempotent_noop=False,
            durability_confirmed=False,
            cleanup_complete=status != "applied_cleanup_incomplete",
            blocked_reason_ids=reasons,
        )
    if status == "blocked":
        return RelayMEMSLPPrimaryReconciliationOutcome(
            **common,
            page_verified=not any("page_" in reason for reason in reasons),
            writes_memory=False,
            index_reconciled=False,
            log_reconciled=False,
            index_updated=False,
            log_updated=False,
            index_idempotent_noop=False,
            log_idempotent_noop=False,
            durability_confirmed=False,
            cleanup_complete=True,
            blocked_reason_ids=reasons,
        )
    return RelayMEMSLPPrimaryReconciliationOutcome(
        **common,
        page_verified=True,
        writes_memory=True,
        index_reconciled=True,
        log_reconciled=True,
        index_updated=True,
        log_updated=True,
        index_idempotent_noop=False,
        log_idempotent_noop=False,
        durability_confirmed=True,
        cleanup_complete=True,
        blocked_reason_ids=reasons,
    )


def m3h(
    *,
    source_status: str = "applied",
    store_state: str = "fully_reconciled",
    classification: str = "recovery_not_required",
    status: str | None = None,
    page_verified: bool = True,
    index_state: str = "proposed",
    log_state: str = "proposed",
    cleanup_present: bool = False,
    reasons: tuple[str, ...] = (),
) -> RelayMEMSLPPrimaryRecoveryAuditOutcome:
    return RelayMEMSLPPrimaryRecoveryAuditOutcome(
        schema_version=M3H_SCHEMA,
        status=status or classification,
        receipt_valid=True,
        source_status=source_status,
        store_state=store_state,
        page_verified=page_verified,
        index_state=index_state,
        log_state=log_state,
        cleanup_artifacts_present=cleanup_present,
        recovery_classification=classification,
        blocked_reason_ids=reasons,
    )


def classify(
    e: object | None,
    g: object | None,
    h: object | None,
    *,
    policy: object | None = None,
) -> RelayMEMSLPPrimaryWorkerOutcome:
    return classify_relaymem_slp_primary_worker_outcome(
        m3e_result=e,
        m3g_result=g,
        m3h_result=h,
        policy_outcome=policy,
    )


def assert_shape(result: RelayMEMSLPPrimaryWorkerOutcome, **expected: object) -> None:
    runtime = result.to_runtime_dict()
    for key, value in expected.items():
        assert runtime[key] == value, (key, runtime[key], value)
