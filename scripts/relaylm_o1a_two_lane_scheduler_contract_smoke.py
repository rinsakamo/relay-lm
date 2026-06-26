#!/usr/bin/env python3
"""Pure O1A two-lane scheduler contract smoke."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from relaylm.relaymem_slp_scheduler_contract import (  # noqa: E402
    MAX_REASON_IDS_PER_LANE,
    ROUND_PROJECTION_SCHEMA,
    LaneOutcome,
    SchedulerGates,
    aggregate_scheduler_round,
)

CANARY = "O1A_USER_ASSISTANT_PROTECTED_CANARY_14f3b2"
FORBIDDEN_TOKENS = (
    CANARY,
    "user_text",
    "assistant_text",
    "protected_source",
    "visible_response",
    "memory_title",
    "memory_summary",
    "memory_body",
    "namespace",
    "character_id",
    "run_id",
    "session_id",
    "turn_id",
    "job_id",
    "dispatch_id",
    "locator_digest",
    "lineage_fingerprint",
    "queue_filename",
    "finalization_filename",
    "store_root",
    "queue_root",
    "protected_source_root",
    "finalization_root",
    "claim_owner",
    "lease_token",
    "generation",
    "revision",
    "retry_not_before",
    "completion_timestamp",
    "record_digest",
    "source_digest",
    "raw_exception",
    "private_delegate_result",
)


def gates(*, mode: str = "apply", replay: bool = True, queue: bool = True) -> SchedulerGates:
    triples = {
        "disabled": (False, True, False),
        "dry_run": (True, True, False),
        "apply": (True, False, True),
    }
    enabled, dry_run_only, apply_enabled = triples[mode]
    return SchedulerGates(
        enabled=enabled,
        dry_run_only=dry_run_only,
        apply_enabled=apply_enabled,
        replay_lane_enabled=replay,
        queue_lane_enabled=queue,
    )


def replay_no_work() -> LaneOutcome:
    return LaneOutcome(
        lane_kind="replay",
        status="no_eligible_work",
        enabled=True,
        attempted=True,
        candidate_observed=False,
        candidate_selected=False,
        canonical_reread_performed=False,
        delegation_attempted=False,
        delegation_completed=False,
        mutation_may_have_occurred=False,
        no_immediate_work=True,
        future_work_hint_present=False,
        contention_observed=False,
        retryable=False,
        unsafe=False,
        terminal_for_candidate=False,
        bounded_reason_ids=("replay_no_eligible_work",),
    )


def replay_completed() -> LaneOutcome:
    return LaneOutcome(
        lane_kind="replay",
        status="completed",
        enabled=True,
        attempted=True,
        candidate_observed=True,
        candidate_selected=True,
        canonical_reread_performed=True,
        delegation_attempted=True,
        delegation_completed=True,
        mutation_may_have_occurred=True,
        no_immediate_work=False,
        future_work_hint_present=False,
        contention_observed=False,
        retryable=False,
        unsafe=False,
        terminal_for_candidate=True,
        bounded_reason_ids=("replay_completed",),
        private_delegate_result={
            "protected_source": CANARY,
            "job_id": "j" * 64,
            "queue_filename": "secret.json",
        },
    )


def replay_busy() -> LaneOutcome:
    return LaneOutcome(
        lane_kind="replay",
        status="busy",
        enabled=True,
        attempted=True,
        candidate_observed=True,
        candidate_selected=False,
        canonical_reread_performed=False,
        delegation_attempted=False,
        delegation_completed=False,
        mutation_may_have_occurred=False,
        no_immediate_work=True,
        future_work_hint_present=False,
        contention_observed=True,
        retryable=True,
        unsafe=False,
        terminal_for_candidate=False,
        bounded_reason_ids=("replay_lock_busy",),
    )


def replay_failed() -> LaneOutcome:
    return LaneOutcome(
        lane_kind="replay",
        status="failed",
        enabled=True,
        attempted=True,
        candidate_observed=True,
        candidate_selected=True,
        canonical_reread_performed=True,
        delegation_attempted=True,
        delegation_completed=False,
        mutation_may_have_occurred=False,
        no_immediate_work=True,
        future_work_hint_present=False,
        contention_observed=False,
        retryable=True,
        unsafe=False,
        terminal_for_candidate=False,
        bounded_reason_ids=("replay_lane_retryable_failure",),
    )


def queue_no_work() -> LaneOutcome:
    return LaneOutcome(
        lane_kind="queue",
        status="no_eligible_work",
        enabled=True,
        attempted=True,
        candidate_observed=False,
        candidate_selected=False,
        canonical_reread_performed=False,
        delegation_attempted=False,
        delegation_completed=False,
        mutation_may_have_occurred=False,
        no_immediate_work=True,
        future_work_hint_present=False,
        contention_observed=False,
        retryable=False,
        unsafe=False,
        terminal_for_candidate=False,
        bounded_reason_ids=("queue_no_eligible_work",),
    )


def queue_future_retry() -> LaneOutcome:
    return LaneOutcome(
        lane_kind="queue",
        status="future_retry_only",
        enabled=True,
        attempted=True,
        candidate_observed=True,
        candidate_selected=False,
        canonical_reread_performed=False,
        delegation_attempted=False,
        delegation_completed=False,
        mutation_may_have_occurred=False,
        no_immediate_work=True,
        future_work_hint_present=True,
        contention_observed=False,
        retryable=True,
        unsafe=False,
        terminal_for_candidate=False,
        bounded_reason_ids=("queue_future_retry_only",),
        private_delegate_result={"retry_not_before": "2099-01-01T00:00:00Z"},
    )


def queue_busy() -> LaneOutcome:
    return LaneOutcome(
        lane_kind="queue",
        status="busy",
        enabled=True,
        attempted=True,
        candidate_observed=False,
        candidate_selected=False,
        canonical_reread_performed=False,
        delegation_attempted=False,
        delegation_completed=False,
        mutation_may_have_occurred=False,
        no_immediate_work=True,
        future_work_hint_present=False,
        contention_observed=True,
        retryable=True,
        unsafe=False,
        terminal_for_candidate=False,
        bounded_reason_ids=("queue_advisory_lock_busy",),
    )


def queue_terminal() -> LaneOutcome:
    return LaneOutcome(
        lane_kind="queue",
        status="terminal",
        enabled=True,
        attempted=True,
        candidate_observed=True,
        candidate_selected=True,
        canonical_reread_performed=True,
        delegation_attempted=True,
        delegation_completed=True,
        mutation_may_have_occurred=True,
        no_immediate_work=False,
        future_work_hint_present=False,
        contention_observed=False,
        retryable=False,
        unsafe=False,
        terminal_for_candidate=True,
        bounded_reason_ids=("queue_terminal_committed",),
        private_delegate_result={
            "user_text": CANARY,
            "lease_token": "secret",
            "store_root": "/secret/store",
        },
    )


def queue_failed() -> LaneOutcome:
    return LaneOutcome(
        lane_kind="queue",
        status="failed",
        enabled=True,
        attempted=True,
        candidate_observed=True,
        candidate_selected=True,
        canonical_reread_performed=True,
        delegation_attempted=True,
        delegation_completed=False,
        mutation_may_have_occurred=False,
        no_immediate_work=True,
        future_work_hint_present=False,
        contention_observed=False,
        retryable=True,
        unsafe=False,
        terminal_for_candidate=False,
        bounded_reason_ids=("queue_lane_retryable_failure",),
    )


def expect_raises(exc_type: type[BaseException], fn, contains: str) -> None:
    try:
        fn()
    except exc_type as exc:
        assert contains in str(exc), (contains, str(exc))
    else:
        raise AssertionError(f"expected_{exc_type.__name__}:{contains}")


def encoded_projection(result) -> str:
    projection = result.projection()
    assert projection["schema_version"] == ROUND_PROJECTION_SCHEMA
    encoded = json.dumps(projection, sort_keys=True, ensure_ascii=True)
    lowered = encoded.lower()
    assert all(token.lower() not in lowered for token in FORBIDDEN_TOKENS)
    assert CANARY not in repr(result)
    return encoded


def main() -> None:
    # 1. replay -> queue fixed ordering; inversion and duplicates fail closed.
    both_idle = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=replay_no_work(), queue_lane=queue_no_work(),
    )
    expect_raises(
        ValueError,
        lambda: aggregate_scheduler_round(
            gates=gates(), invocation_order=("queue", "replay"),
            replay_lane=replay_no_work(), queue_lane=queue_no_work(),
        ),
        "invalid_lane_invocation_order",
    )

    # 2-3. at most one delegation per lane and at most two total.
    both_work = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=replay_completed(), queue_lane=queue_terminal(),
    )
    assert both_work.work_units_attempted == 2
    assert both_work.work_units_completed == 2

    # 4. replay success / queue no-work.
    replay_progress = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=replay_completed(), queue_lane=queue_no_work(),
    )
    assert replay_progress.disposition == "run_next_round"
    assert replay_progress.work_units_completed == 1

    # 5. replay no-work / queue execution.
    queue_progress = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=replay_no_work(), queue_lane=queue_terminal(),
    )
    assert queue_progress.disposition == "run_next_round"
    assert queue_progress.work_units_completed == 1

    # 6. both lanes work.
    assert both_work.status == "round_completed"
    assert both_work.disposition == "run_next_round"

    # 7. both no-work -> idle.
    assert both_idle.status == "idle"
    assert both_idle.disposition == "idle"
    assert both_idle.idle_recommended

    # 8. future retry only -> idle; exact timestamp remains private.
    future = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=replay_no_work(), queue_lane=queue_future_retry(),
    )
    assert future.disposition == "idle"
    assert future.future_work_hint_present
    assert "2099" not in encoded_projection(future)

    # 9. lane busy is an idle candidate, not permanent no-work.
    busy = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=replay_busy(), queue_lane=queue_busy(),
    )
    assert busy.disposition == "idle"
    assert busy.retryable

    # 10. replay failure does not suppress queue opportunity.
    replay_failure_queue_success = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=replay_failed(), queue_lane=queue_terminal(),
    )
    assert replay_failure_queue_success.queue_lane is not None
    assert replay_failure_queue_success.queue_lane.delegation_completed
    assert replay_failure_queue_success.status == "partial_progress"

    # 11. queue failure cannot roll back completed replay.
    replay_success_queue_failure = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=replay_completed(), queue_lane=queue_failed(),
    )
    assert replay_success_queue_failure.replay_lane is not None
    assert replay_success_queue_failure.replay_lane.delegation_completed
    assert replay_success_queue_failure.status == "partial_progress"

    # 12. disabled mode invokes no lanes.
    disabled = aggregate_scheduler_round(
        gates=gates(mode="disabled"), invocation_order=(), replay_lane=None, queue_lane=None,
    )
    assert disabled.status == "disabled" and disabled.disposition == "stop"
    expect_raises(
        ValueError,
        lambda: aggregate_scheduler_round(
            gates=gates(mode="disabled"), invocation_order=("replay",),
            replay_lane=replay_no_work(), queue_lane=None,
        ),
        "disabled_scheduler_must_not_invoke_lanes",
    )

    # 13. invalid gates stop before lane invocation.
    invalid = SchedulerGates(
        enabled=True, dry_run_only=True, apply_enabled=True,
        replay_lane_enabled=True, queue_lane_enabled=True,
    )
    invalid_result = aggregate_scheduler_round(
        gates=invalid, invocation_order=(), replay_lane=None, queue_lane=None,
    )
    assert invalid_result.status == "invalid_configuration"
    assert invalid_result.disposition == "stop"

    # 14. replay private output is not a queue input or projection field.
    assert replay_progress.queue_lane is not None
    assert replay_progress.queue_lane.status == "no_eligible_work"
    replay_encoded = encoded_projection(replay_progress)
    assert "secret.json" not in replay_encoded and "j" * 64 not in replay_encoded

    # 15-16. nested private results, identities, paths, timestamps, and content do not leak.
    both_encoded = encoded_projection(both_work)
    assert "secret" not in both_encoded

    # 17. reason bounds are exact and overflow fails closed.
    exact_reasons = tuple(f"reason_{index}" for index in range(MAX_REASON_IDS_PER_LANE))
    exact = LaneOutcome(
        lane_kind="replay", status="no_eligible_work", enabled=True, attempted=True,
        candidate_observed=False, candidate_selected=False,
        canonical_reread_performed=False, delegation_attempted=False,
        delegation_completed=False, mutation_may_have_occurred=False,
        no_immediate_work=True, future_work_hint_present=False,
        contention_observed=False, retryable=False, unsafe=False,
        terminal_for_candidate=False, bounded_reason_ids=exact_reasons,
    )
    assert len(exact.bounded_reason_ids) == MAX_REASON_IDS_PER_LANE
    expect_raises(
        ValueError,
        lambda: LaneOutcome(
            lane_kind="replay", status="no_eligible_work", enabled=True, attempted=True,
            candidate_observed=False, candidate_selected=False,
            canonical_reread_performed=False, delegation_attempted=False,
            delegation_completed=False, mutation_may_have_occurred=False,
            no_immediate_work=True, future_work_hint_present=False,
            contention_observed=False, retryable=False, unsafe=False,
            terminal_for_candidate=False,
            bounded_reason_ids=exact_reasons + ("reason_overflow",),
        ),
        "lane_reason_ids_too_many",
    )

    # 18. unknown status fails closed.
    expect_raises(
        ValueError,
        lambda: LaneOutcome(
            lane_kind="replay", status="invented_success", enabled=True, attempted=True,  # type: ignore[arg-type]
            candidate_observed=False, candidate_selected=False,
            canonical_reread_performed=False, delegation_attempted=False,
            delegation_completed=False, mutation_may_have_occurred=False,
            no_immediate_work=True, future_work_hint_present=False,
            contention_observed=False, retryable=False, unsafe=False,
            terminal_for_candidate=False,
        ),
        "unknown_lane_status",
    )

    # 19. bool/int/string coercion is rejected.
    expect_raises(
        TypeError,
        lambda: SchedulerGates(
            enabled=1, dry_run_only=False, apply_enabled=True,  # type: ignore[arg-type]
            replay_lane_enabled=True, queue_lane_enabled=True,
        ),
        "enabled_must_be_bool",
    )

    # 20. identical input yields identical projection.
    again = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=replay_completed(), queue_lane=queue_terminal(),
    )
    assert encoded_projection(both_work) == encoded_projection(again)

    # 21. O1B may learn replay contention only after I1-GC returns.
    delegated_busy = LaneOutcome(
        lane_kind="replay", status="busy", enabled=True, attempted=True,
        candidate_observed=True, candidate_selected=True,
        canonical_reread_performed=True, delegation_attempted=True,
        delegation_completed=True, mutation_may_have_occurred=False,
        no_immediate_work=True, future_work_hint_present=False,
        contention_observed=True, retryable=True, unsafe=False,
        terminal_for_candidate=False, bounded_reason_ids=("replay_delegate_busy",),
    )
    busy_after_delegate = aggregate_scheduler_round(
        gates=gates(), invocation_order=("replay", "queue"),
        replay_lane=delegated_busy, queue_lane=queue_no_work(),
    )
    assert busy_after_delegate.disposition == "idle"
    assert busy_after_delegate.work_units_completed == 1

    # 22. A returned replay dry-run delegation is complete but does not force a round.
    delegated_dry_run = LaneOutcome(
        lane_kind="replay", status="delegated", enabled=True, attempted=True,
        candidate_observed=True, candidate_selected=True,
        canonical_reread_performed=True, delegation_attempted=True,
        delegation_completed=True, mutation_may_have_occurred=False,
        no_immediate_work=True, future_work_hint_present=False,
        contention_observed=False, retryable=False, unsafe=False,
        terminal_for_candidate=False, bounded_reason_ids=("replay_delegate_dry_run",),
    )
    dry_round = aggregate_scheduler_round(
        gates=gates(mode="dry_run"), invocation_order=("replay", "queue"),
        replay_lane=delegated_dry_run, queue_lane=queue_no_work(),
    )
    assert dry_round.disposition == "idle"
    assert dry_round.work_units_completed == 1

    print("RelayLM O1A two-lane scheduler contract smoke passed.")


if __name__ == "__main__":
    main()
