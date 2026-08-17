from __future__ import annotations

import asyncio

from relaylm.evaluation import evaluate_memory_heading_retrieval


def test_memory_heading_retrieval_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_memory_heading_retrieval())

    assert result.scenario_id == "memory_heading_retrieval"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "memory_retrieval",
        "memory_budget",
    }
    assert result.metrics == {
        "relevant_selected_count": 1,
        "irrelevant_selected_count": 0,
        "oversized_selected_count": 1,
    }
