"""Terminal failure mappings for the Phase 6-C1 outcome smoke."""
from relaylm.relaymem_slp_primary_worker_outcome import (
    RelayMEMSLPPrimaryPolicyOutcome,
)
from relaylm_phase6c1_primary_worker_outcome_support import (
    POLICY_SCHEMA,
    assert_shape,
    classify,
    m3e_applied,
    m3g,
    m3h,
)


def run_terminal_cases() -> tuple[object, ...]:
    held = classify(
        None,
        None,
        None,
        policy=RelayMEMSLPPrimaryPolicyOutcome(
            POLICY_SCHEMA,
            "held",
            "promotion_policy_blocks_autonomous_apply:review_required",
        ),
    )
    assert_shape(
        held,
        transition_kind="commit_failed",
        failure_class="memory_policy_held",
        policy_held=True,
        terminal=True,
    )
    blocked = classify(
        None,
        None,
        None,
        policy=RelayMEMSLPPrimaryPolicyOutcome(
            POLICY_SCHEMA,
            "blocked",
            "promotion_policy_blocks_autonomous_apply:never_auto_promote",
        ),
    )
    assert_shape(
        blocked,
        transition_kind="commit_failed",
        failure_class="memory_policy_blocked",
    )

    manual = classify(
        m3e_applied(),
        m3g("applied_durability_unconfirmed"),
        m3h(
            source_status="applied_durability_unconfirmed",
            classification="manual_confirmation_required",
        ),
    )
    assert_shape(
        manual,
        transition_kind="commit_failed",
        failure_class="manual_confirmation_required",
        manual_confirmation_required=True,
        retryable=False,
        terminal=True,
    )
    journal = classify(
        m3e_applied(),
        m3g("applied_state_uncertain"),
        m3h(
            source_status="applied_state_uncertain",
            store_state="state_diverged",
            classification="journaled_recovery_candidate",
            index_state="diverged",
            log_state="invalid",
        ),
    )
    assert_shape(
        journal,
        transition_kind="commit_failed",
        failure_class="recovery_isolation_required",
        recovery_isolation_required=True,
    )

    page_missing = classify(
        m3e_applied(),
        m3g(
            "blocked",
            reasons=("primary_reconciliation_apply_page_missing",),
        ),
        None,
    )
    assert_shape(
        page_missing,
        transition_kind="commit_failed",
        failure_class="store_conflict",
    )
    page_digest = classify(
        m3e_applied(),
        m3g(
            "blocked",
            reasons=("primary_reconciliation_apply_page_digest_mismatch",),
        ),
        None,
    )
    assert_shape(
        page_digest,
        transition_kind="commit_failed",
        failure_class="store_corruption",
    )
    index_conflict = classify(
        m3e_applied(),
        m3g(
            "blocked",
            reasons=(
                "primary_reconciliation_apply_index_current_state_conflict",
            ),
        ),
        None,
    )
    assert_shape(
        index_conflict,
        transition_kind="commit_failed",
        failure_class="store_conflict",
    )
    diverged = classify(
        m3e_applied(),
        m3g(),
        m3h(
            store_state="state_diverged",
            classification="manual_confirmation_required",
            index_state="diverged",
            log_state="invalid",
        ),
    )
    assert_shape(
        diverged,
        transition_kind="commit_failed",
        failure_class="store_conflict",
    )

    uncertain_retry = classify(
        m3e_applied(),
        m3g("applied_state_uncertain"),
        m3h(
            source_status="applied_state_uncertain",
            store_state="index_applied_log_pending",
            classification="retry_reconciliation",
            index_state="proposed",
            log_state="expected",
        ),
    )
    assert_shape(
        uncertain_retry,
        transition_kind="retry_release",
        retry_class="primary_reconciliation_retry",
    )
    return (
        held,
        blocked,
        manual,
        journal,
        page_missing,
        page_digest,
        index_conflict,
        diverged,
        uncertain_retry,
    )
