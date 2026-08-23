from __future__ import annotations

import asyncio

from relaylm.evaluation_context import evaluate_targeted_event_retrieval


def test_targeted_event_retrieval_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_targeted_event_retrieval())

    assert result.scenario_id == "targeted_event_retrieval"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "event_retrieval",
        "event_budget",
        "event_provenance",
    }
    assert result.metrics == {
        "relevant_selected_count": 1,
        "irrelevant_selected_count": 0,
        "excluded_current_selected_count": 1,
        "oversized_selected_count": 1,
        "ranked_selected_count": 2,
        "tie_selected_count": 1,
        "token_boundary_selected_count": 1,
    }
