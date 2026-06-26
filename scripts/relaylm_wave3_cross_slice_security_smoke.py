#!/usr/bin/env python3
"""Wave 3 cross-slice content-free projection and leakage smoke."""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

from relaylm.relaymem_slp_scheduler_contract import LaneOutcome, SchedulerRoundResult

ROOT = Path(__file__).resolve().parents[1]

CONCRETE_CANARIES = (
    "USER_CONTENT_CANARY_W3",
    "MODEL_OUTPUT_CANARY_W3",
    "MEMORY_SUMMARY_TITLE_CANARY_W3",
    "FORGET_REASON_CANARY_W3",
    "TOMBSTONE_CONTENT_CANARY_W3",
    "I1G_LOCATOR_CANARY_W3",
    "QUEUE_ROOT_PATH_CANARY_W3",
    "JOB_ID_CANARY_W3",
    "DISPATCH_ID_CANARY_W3",
    "CLAIM_TOKEN_CANARY_W3",
    "CHARACTER_PRIVATE_SCOPE_CANARY_W3",
    "RAW_EXCEPTION_CANARY_W3",
    "PRIVATE_TIMESTAMP_CANARY_W3",
)

PUBLIC_DOCS = (
    "docs/architecture/wave3_cross_slice_convergence_audit.md",
    "docs/architecture/i1ge_durable_finalization_crash_validation.md",
    "docs/architecture/phase_i4d_primary_retrieval_exclusion.md",
    "docs/architecture/o1d1_production_scheduler_round.md",
    "docs/mvp/wave3/i1ge_completion_report.md",
    "docs/mvp/wave3/i4d_completion_report.md",
    "docs/mvp/wave3/o1d1_completion_report.md",
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def assert_no_canary(value: object, context: str) -> None:
    text = repr(value)
    leaked = [canary for canary in CONCRETE_CANARIES if canary in text]
    assert not leaked, f"{context}: leaked concrete canaries {leaked!r}"


def scheduler_projection_is_content_free() -> None:
    private_payload = {name: name for name in CONCRETE_CANARIES}
    replay = LaneOutcome(
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
        private_delegate_result=private_payload,
    )
    queue = LaneOutcome(
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
        bounded_reason_ids=("queue_terminal",),
        private_delegate_result=private_payload,
    )
    result = SchedulerRoundResult(
        status="round_completed",
        disposition="run_next_round",
        replay_lane=replay,
        queue_lane=queue,
        work_units_attempted=2,
        work_units_completed=2,
        idle_recommended=False,
        immediate_next_round_recommended=True,
        future_work_hint_present=False,
        retryable=False,
        unsafe=False,
        bounded_reason_ids=("replay_completed", "queue_terminal"),
    )
    assert_no_canary(replay, "replay lane repr")
    assert_no_canary(queue, "queue lane repr")
    assert_no_canary(result, "round result repr")
    assert_no_canary(result.projection(), "round projection")
    assert replay == LaneOutcome(
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
        private_delegate_result={"different": "PRIVATE_TIMESTAMP_CANARY_W3"},
    )


def docs_are_content_free() -> None:
    for path in PUBLIC_DOCS:
        body = read(path)
        leaked = [canary for canary in CONCRETE_CANARIES if canary in body]
        assert not leaked, f"{path}: leaked concrete canaries {leaked!r}"


def combined_smoke_output_is_content_free() -> None:
    import relaylm_wave3_cross_slice_convergence_smoke as convergence

    stream = io.StringIO()
    with redirect_stdout(stream):
        convergence.main()
    assert_no_canary(stream.getvalue(), "combined convergence smoke output")


def main() -> None:
    scheduler_projection_is_content_free()
    docs_are_content_free()
    combined_smoke_output_is_content_free()
    print("Wave 3 cross-slice security smoke passed")


if __name__ == "__main__":
    main()
