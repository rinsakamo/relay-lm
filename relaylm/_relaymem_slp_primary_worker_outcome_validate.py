"""Strict validation for Phase 6-C1 Primary MEM outcome snapshots."""
from __future__ import annotations

from ._relaymem_slp_primary_worker_outcome_types import (
    M3E_SCHEMA,
    M3G_SCHEMA,
    M3H_SCHEMA,
    POLICY_SCHEMA,
    SOURCE_CORRELATION_SCHEMA,
    RelayMEMSLPPrimaryPageWriteOutcome,
    RelayMEMSLPPrimaryPolicyOutcome,
    RelayMEMSLPPrimaryReconciliationOutcome,
    RelayMEMSLPPrimaryRecoveryAuditOutcome,
    RelayMEMSLPPrimarySourceCorrelationOutcome,
)

M3E_UNCERTAIN = frozenset({
    "applied_durability_unconfirmed",
    "applied_cleanup_incomplete",
    "applied_state_uncertain",
})
M3G_UNCERTAIN = frozenset(M3E_UNCERTAIN)
M3G_LOCK_REASON = "primary_reconciliation_apply_lock_unavailable"
M3H_LOCK_REASON = "primary_reconciliation_recovery_lock_unavailable"

_M3E_STATUSES = frozenset({
    "disabled", "dry_run_ready", "applied", "already_applied", "blocked",
    *M3E_UNCERTAIN,
})
_M3G_STATUSES = frozenset({
    "disabled", "blocked", "dry_run_ready", "resume_ready", "already_applied",
    "applied", "index_applied_log_pending", *M3G_UNCERTAIN,
})
_M3H_STATUSES = frozenset({
    "disabled", "blocked", "recovery_not_required", "retry_reconciliation",
    "manual_confirmation_required", "journaled_recovery_candidate",
})
_STORE_STATES = frozenset({
    "fully_reconciled", "index_applied_log_pending", "not_applied",
    "log_applied_index_pending", "page_unverified", "control_unverified",
    "state_diverged", "not_evaluated",
})
_CONTROL_STATES = frozenset({
    "expected", "proposed", "diverged", "missing", "invalid", "not_checked",
})
_RECOVERY_CLASSES = frozenset({
    "recovery_not_required", "retry_reconciliation",
    "manual_confirmation_required", "journaled_recovery_candidate",
    "not_evaluated",
})
_MAX_REASON_IDS = 24
_MAX_REASON_ID_LENGTH = 128


def validate_inputs(
    *,
    m3e_result: object | None,
    m3g_result: object | None,
    m3h_result: object | None,
    policy_outcome: object | None,
    source_correlation: object | None,
) -> tuple[str, ...]:
    errors: list[str] = []
    _validate_exact(
        m3e_result, RelayMEMSLPPrimaryPageWriteOutcome,
        "exact_m3e_result_required", _validate_m3e, errors,
    )
    _validate_exact(
        m3g_result, RelayMEMSLPPrimaryReconciliationOutcome,
        "exact_m3g_result_required", _validate_m3g, errors,
    )
    _validate_exact(
        m3h_result, RelayMEMSLPPrimaryRecoveryAuditOutcome,
        "exact_m3h_result_required", _validate_m3h, errors,
    )
    if policy_outcome is not None:
        if type(policy_outcome) is not RelayMEMSLPPrimaryPolicyOutcome:
            errors.append("exact_policy_outcome_required")
        else:
            if policy_outcome.schema_version != POLICY_SCHEMA:
                errors.append("policy_schema_version_invalid")
            if policy_outcome.status not in {"held", "blocked"}:
                errors.append("policy_status_invalid")
            if not valid_reason_id(policy_outcome.reason_id):
                errors.append("policy_reason_id_invalid")
    if source_correlation is not None:
        if type(source_correlation) is not RelayMEMSLPPrimarySourceCorrelationOutcome:
            errors.append("exact_source_correlation_outcome_required")
        else:
            if source_correlation.schema_version != SOURCE_CORRELATION_SCHEMA:
                errors.append("source_correlation_schema_version_invalid")
            if source_correlation.status not in {"verified", "invalid"}:
                errors.append("source_correlation_status_invalid")
    return dedupe(errors)


def _validate_exact(value, expected_type, reason, validator, errors) -> None:
    if value is None:
        return
    if type(value) is not expected_type:
        errors.append(reason)
    else:
        errors.extend(validator(value))


def _validate_m3e(value: RelayMEMSLPPrimaryPageWriteOutcome) -> tuple[str, ...]:
    errors: list[str] = []
    if value.schema_version != M3E_SCHEMA:
        errors.append("m3e_schema_version_invalid")
    if value.status not in _M3E_STATUSES:
        errors.append("m3e_status_invalid")
    _strict_bools(
        value,
        ("handoff_valid", "writes_memory", "page_applied", "idempotent_noop",
         "durability_confirmed", "cleanup_complete"),
        "m3e", errors,
    )
    errors.extend(validate_reason_ids(value.blocked_reason_ids, "m3e"))
    if value.status == "applied" and not (
        value.handoff_valid and value.writes_memory and value.page_applied
        and not value.idempotent_noop and value.durability_confirmed
        and value.cleanup_complete and not value.blocked_reason_ids
    ):
        errors.append("m3e_applied_invariant_invalid")
    if value.status == "already_applied" and not (
        value.handoff_valid and not value.writes_memory and value.page_applied
        and value.idempotent_noop and not value.durability_confirmed
        and value.cleanup_complete and not value.blocked_reason_ids
    ):
        errors.append("m3e_already_applied_invariant_invalid")
    if value.status in M3E_UNCERTAIN and not (
        value.handoff_valid and value.writes_memory and value.page_applied
    ):
        errors.append("m3e_uncertain_invariant_invalid")
    return dedupe(errors)


def _validate_m3g(value: RelayMEMSLPPrimaryReconciliationOutcome) -> tuple[str, ...]:
    errors: list[str] = []
    if value.schema_version != M3G_SCHEMA:
        errors.append("m3g_schema_version_invalid")
    if value.status not in _M3G_STATUSES:
        errors.append("m3g_status_invalid")
    _strict_bools(
        value,
        ("plan_valid", "page_verified", "writes_memory", "index_reconciled",
         "log_reconciled", "index_updated", "log_updated",
         "index_idempotent_noop", "log_idempotent_noop",
         "durability_confirmed", "cleanup_complete"),
        "m3g", errors,
    )
    errors.extend(validate_reason_ids(value.blocked_reason_ids, "m3g"))
    if value.status == "applied" and not (
        value.plan_valid and value.page_verified and value.index_reconciled
        and value.log_reconciled and value.durability_confirmed
        and value.cleanup_complete and not value.blocked_reason_ids
    ):
        errors.append("m3g_applied_invariant_invalid")
    if value.status == "already_applied" and not (
        value.plan_valid and value.page_verified and value.index_reconciled
        and value.log_reconciled and value.index_idempotent_noop
        and value.log_idempotent_noop and value.durability_confirmed
        and value.cleanup_complete and not value.blocked_reason_ids
    ):
        errors.append("m3g_already_applied_invariant_invalid")
    if value.status == "index_applied_log_pending" and not (
        value.plan_valid and value.page_verified and value.index_reconciled
        and not value.log_reconciled
    ):
        errors.append("m3g_partial_invariant_invalid")
    if value.status in M3G_UNCERTAIN and not (
        value.plan_valid and value.page_verified
    ):
        errors.append("m3g_uncertain_invariant_invalid")
    return dedupe(errors)


def _validate_m3h(value: RelayMEMSLPPrimaryRecoveryAuditOutcome) -> tuple[str, ...]:
    errors: list[str] = []
    if value.schema_version != M3H_SCHEMA:
        errors.append("m3h_schema_version_invalid")
    if value.status not in _M3H_STATUSES:
        errors.append("m3h_status_invalid")
    if value.source_status not in _M3G_STATUSES:
        errors.append("m3h_source_status_invalid")
    if value.store_state not in _STORE_STATES:
        errors.append("m3h_store_state_invalid")
    if value.index_state not in _CONTROL_STATES:
        errors.append("m3h_index_state_invalid")
    if value.log_state not in _CONTROL_STATES:
        errors.append("m3h_log_state_invalid")
    if value.recovery_classification not in _RECOVERY_CLASSES:
        errors.append("m3h_recovery_classification_invalid")
    _strict_bools(
        value,
        ("receipt_valid", "page_verified", "cleanup_artifacts_present"),
        "m3h", errors,
    )
    errors.extend(validate_reason_ids(value.blocked_reason_ids, "m3h"))
    if value.status not in {"blocked", "disabled"} and (
        value.status != value.recovery_classification
    ):
        errors.append("m3h_status_classification_mismatch")
    if value.status == "recovery_not_required" and not value.receipt_valid:
        errors.append("m3h_recovery_not_required_receipt_invalid")
    return dedupe(errors)


def _strict_bools(value, fields, prefix: str, errors: list[str]) -> None:
    for field in fields:
        if type(getattr(value, field)) is not bool:
            errors.append(f"{prefix}_{field}_invalid")


def validate_reason_ids(value: object, prefix: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        return (f"{prefix}_blocked_reason_ids_invalid",)
    if len(value) > _MAX_REASON_IDS:
        return (f"{prefix}_blocked_reason_ids_limit_exceeded",)
    errors: list[str] = []
    if len(set(value)) != len(value):
        errors.append(f"{prefix}_blocked_reason_ids_duplicate")
    if any(not valid_reason_id(item) for item in value):
        errors.append(f"{prefix}_blocked_reason_id_invalid")
    return dedupe(errors)


def valid_reason_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= _MAX_REASON_ID_LENGTH
        and all(ch.islower() or ch.isdigit() or ch in "_:-" for ch in value)
    )


def dedupe(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))
