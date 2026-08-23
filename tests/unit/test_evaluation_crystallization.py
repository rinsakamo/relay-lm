from __future__ import annotations

import asyncio

from relaylm.evaluation_crystallization import evaluate_crystallization_integrity


def test_crystallization_evaluation_keeps_markdown_and_state_authority_distinct() -> None:
    result = asyncio.run(evaluate_crystallization_integrity())

    assert result.scenario_id == "crystallization_integrity"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "crystallized_memory",
        "validator",
        "canonical_state",
        "crystallizer",
    }
    assert result.metrics == {
        "crystallizer_calls": 2,
        "first_pass_accepted_count": 1,
        "first_pass_rejected_count": 1,
        "final_state_count": 1,
    }
