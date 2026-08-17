from __future__ import annotations

import asyncio

from relaylm.evaluation import evaluate_streaming_safety


def test_streaming_safety_evaluation_covers_complete_truncated_and_cancelled_turns() -> None:
    result = asyncio.run(evaluate_streaming_safety())

    assert result.scenario_id == "streaming_safety"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "stream_delivery",
        "event_journal",
        "canonical_state",
        "cancellation",
    }
    assert result.metrics == {
        "successful_event_count": 2,
        "successful_state_count": 1,
        "truncated_event_count": 1,
        "cancelled_event_count": 1,
    }
