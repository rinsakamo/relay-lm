from __future__ import annotations

import asyncio

from relaylm.evaluation_total_budget_accounting import evaluate_total_budget_accounting


def test_total_budget_accounting_component() -> None:
    result = asyncio.run(evaluate_total_budget_accounting())

    assert result.scenario_id == "total_budget_accounting"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "hard_capacity_equation_preserved",
        "protected_floor_overflow_exposed",
        "output_reserve_overflow_exposed",
        "invalid_explicit_counts_rejected",
        "budget_types_require_explicit_counts",
    }
    assert {check.boundary for check in result.checks} == {"cognitive_budget"}
    assert result.metrics == {
        "accounting_fixture_count": 3,
        "protected_floor_fit_count": 1,
        "overflow_fixture_count": 2,
        "invalid_count_rejection_count": 4,
        "missing_argument_rejection_count": 2,
    }
