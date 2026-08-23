from __future__ import annotations

import asyncio

from relaylm.evaluation_correction import evaluate_correction_remove_semantics


def test_correction_remove_evaluation_closes_current_state_but_preserves_history() -> None:
    result = asyncio.run(evaluate_correction_remove_semantics())

    assert result.scenario_id == "correction_remove_semantics"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "validator",
        "canonical_state",
        "event_journal",
    }
    assert result.metrics == {
        "remove_decision_count": 1,
        "post_remove_state_count": 0,
        "persisted_event_count": 2,
        "weakening_state_count": 1,
    }
