from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_serialized_input_fit as evaluation_module
from relaylm.evaluation_serialized_input_fit import evaluate_serialized_input_fit_component


def test_serialized_input_fit_component_uses_real_fit_api() -> None:
    with patch.object(
        evaluation_module,
        "evaluate_serialized_input_fit",
        wraps=evaluation_module.evaluate_serialized_input_fit,
    ) as evaluate_fit:
        result = asyncio.run(evaluate_serialized_input_fit_component())

    assert evaluate_fit.call_count == 3
    assert result.scenario_id == "serialized_input_fit"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "exact_count_preserves_serialized_accounting",
        "conservative_estimate_is_explicit_mode",
        "final_serialized_count_controls_hard_fit",
        "oversized_output_reserve_cannot_fit_empty_input",
        "invalid_counts_and_untyped_modes_are_rejected",
    }
    assert {check.boundary for check in result.checks} == {"cognitive_budget"}
    assert result.metrics == {
        "fit_evaluation_count": 3,
        "count_mode_count": 2,
        "fit_case_count": 1,
        "overflow_case_count": 2,
        "invalid_input_rejection_count": 6,
    }
