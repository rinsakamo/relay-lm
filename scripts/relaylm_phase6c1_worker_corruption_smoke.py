"""Worker-level corruption, divergence, and uncertainty smoke for C1-4."""
from __future__ import annotations

from relaylm_phase6c1_primary_worker_smoke import run_outcome_case
from relaylm_phase6c1_primary_worker_test_support import full_m3h, m3g_result


def _audit_state(
    store_state: str,
    *,
    page_verified: bool,
    index_state: str,
    log_state: str,
    source_status: str = "applied",
    classification: str = "manual_confirmation_required",
) -> dict[str, object]:
    value = full_m3h(classification)
    value.update(
        status=classification,
        source_status=source_status,
        store_state=store_state,
        recovery_classification=classification,
        blocked_reasons=[],
    )
    value["projection"] = {
        "page_verified": page_verified,
        "index_state": index_state,
        "log_state": log_state,
        "cleanup_artifacts_present": False,
    }
    return value


def m3g_store_failure_matrix() -> None:
    cases = (
        (
            "page-missing",
            "primary_reconciliation_apply_page_missing",
            "store_conflict",
        ),
        (
            "page-digest-mismatch",
            "primary_reconciliation_apply_page_digest_mismatch",
            "store_corruption",
        ),
        (
            "malformed-index",
            "primary_reconciliation_index_current_contract_invalid",
            "store_corruption",
        ),
        (
            "conflicting-index",
            "primary_reconciliation_apply_index_conflict",
            "store_conflict",
        ),
        (
            "conflicting-log",
            "primary_reconciliation_apply_log_conflict",
            "store_conflict",
        ),
        (
            "non-utf8-control",
            "primary_reconciliation_index_utf8_invalid",
            "store_corruption",
        ),
        (
            "control-symlink",
            "primary_reconciliation_index_symlink_blocked",
            "store_corruption",
        ),
        (
            "unsafe-control-file-type",
            "primary_reconciliation_index_file_not_regular",
            "store_corruption",
        ),
    )
    for name, reason, failure_class in cases:
        run_outcome_case(
            name,
            m3g=m3g_result("blocked", reason),
            expected_status="terminal_failed",
            expected_state="failed",
            failure_class=failure_class,
        )


def m3h_divergence_matrix() -> None:
    run_outcome_case(
        "state-diverged",
        m3g=m3g_result("applied"),
        m3h=_audit_state(
            "state_diverged",
            page_verified=True,
            index_state="diverged",
            log_state="invalid",
        ),
        expected_status="terminal_failed",
        expected_state="failed",
        failure_class="store_conflict",
    )
    run_outcome_case(
        "page-unverified",
        m3g=m3g_result("applied"),
        m3h=_audit_state(
            "page_unverified",
            page_verified=False,
            index_state="not_checked",
            log_state="not_checked",
        ),
        expected_status="terminal_failed",
        expected_state="failed",
        failure_class="store_corruption",
    )
    run_outcome_case(
        "control-unverified",
        m3g=m3g_result("applied"),
        m3h=_audit_state(
            "control_unverified",
            page_verified=True,
            index_state="invalid",
            log_state="invalid",
        ),
        expected_status="terminal_failed",
        expected_state="failed",
        failure_class="store_corruption",
    )


def durability_uncertainty_is_not_success() -> None:
    run_outcome_case(
        "durability-uncertain",
        m3g=m3g_result("applied_durability_unconfirmed"),
        m3h=_audit_state(
            "control_unverified",
            page_verified=True,
            index_state="invalid",
            log_state="invalid",
            source_status="applied_durability_unconfirmed",
            classification="manual_confirmation_required",
        ),
        expected_status="terminal_failed",
        expected_state="failed",
        failure_class="manual_confirmation_required",
    )


def main() -> int:
    m3g_store_failure_matrix()
    m3h_divergence_matrix()
    durability_uncertainty_is_not_success()
    print("Phase 6-C1 integrated worker corruption smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
