from __future__ import annotations

import asyncio

from relaylm.evaluation import evaluate_working_context_budget_diagnostics


def test_working_context_budget_diagnostics_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_working_context_budget_diagnostics())

    assert result.scenario_id == "working_context_budget_diagnostics"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "context_compiler",
        "diagnostics",
    }
    assert result.metrics == {
        "event_window_evicted_count": 1,
        "orphan_assistant_evicted_count": 1,
        "character_budget_evicted_count": 2,
        "zero_character_budget_evicted_count": 4,
    }
