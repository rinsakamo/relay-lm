"""Success and retry mappings for the Phase 6-C1 outcome smoke."""
from relaylm_phase6c1_primary_worker_outcome_support import (
    assert_shape,
    classify,
    m3e_applied,
    m3e_idempotent,
    m3g,
    m3h,
)


def run_success_retry_cases() -> tuple[object, ...]:
    exact = classify(m3e_applied(), m3g(), m3h())
    assert_shape(
        exact,
        transition_kind="commit_succeeded",
        terminal_state="succeeded",
        retryable=False,
        terminal=True,
        durable_success_verified=True,
        terminal_reason_id="primary_mem_durable_state_verified",
    )
    idem = classify(
        m3e_idempotent(),
        m3g("already_applied"),
        m3h(source_status="already_applied"),
    )
    assert_shape(
        idem,
        transition_kind="commit_succeeded",
        durable_success_verified=True,
    )

    lock_g = classify(
        m3e_applied(),
        m3g(
            "blocked",
            reasons=("primary_reconciliation_apply_lock_unavailable",),
        ),
        None,
    )
    assert_shape(
        lock_g,
        transition_kind="retry_release",
        retry_class="transient_lock_contention",
        failure_class="resource_contention",
        retryable=True,
        terminal=False,
    )
    lock_h = classify(
        m3e_applied(),
        m3g(),
        m3h(
            status="blocked",
            store_state="not_evaluated",
            classification="not_evaluated",
            page_verified=False,
            index_state="not_checked",
            log_state="not_checked",
            reasons=("primary_reconciliation_recovery_lock_unavailable",),
        ),
    )
    assert_shape(
        lock_h,
        transition_kind="retry_release",
        retry_class="transient_lock_contention",
    )

    partial = classify(
        m3e_applied(),
        m3g("index_applied_log_pending"),
        m3h(
            source_status="index_applied_log_pending",
            store_state="index_applied_log_pending",
            classification="retry_reconciliation",
            index_state="proposed",
            log_state="expected",
        ),
    )
    assert_shape(
        partial,
        transition_kind="retry_release",
        retry_class="primary_reconciliation_retry",
        failure_class="partial_progress_verified",
    )
    return exact, idem, lock_g, lock_h, partial
