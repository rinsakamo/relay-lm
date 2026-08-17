from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_serialized_fit_enforcement as evaluation_module
from relaylm.evaluation_serialized_fit_enforcement import (
    evaluate_serialized_fit_enforcement,
)


def test_serialized_fit_enforcement_component_uses_real_enforcement_api() -> None:
    with patch.object(
        evaluation_module,
        "enforce_serialized_input_budget",
        wraps=evaluation_module.enforce_serialized_input_budget,
    ) as enforce:
        result = asyncio.run(evaluate_serialized_fit_enforcement())

    assert enforce.call_count == 7
    assert result.scenario_id == "serialized_fit_enforcement"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "initial_fit_returns_without_pressure",
        "overflow_recompiles_with_explicit_degraded_plan",
        "degradation_exhaustion_raises_bounded_failure",
        "same_inputs_produce_same_enforcement_sequence",
        "untyped_compiler_and_counter_results_are_rejected",
    }
    assert {check.boundary for check in result.checks} == {"cognitive_budget"}
    assert result.metrics == {
        "enforcement_call_count": 7,
        "fit_case_count": 3,
        "degraded_fit_case_count": 2,
        "bounded_failure_count": 1,
        "invalid_result_rejection_count": 2,
    }
