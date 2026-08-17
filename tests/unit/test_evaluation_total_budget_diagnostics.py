from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_total_budget_diagnostics as evaluation_module
from relaylm.evaluation_total_budget_diagnostics import (
    evaluate_total_budget_diagnostics,
)


def test_total_budget_diagnostics_component_uses_real_diagnostic_apis() -> None:
    with (
        patch.object(
            evaluation_module,
            "diagnostics_for_budget_result",
            wraps=evaluation_module.diagnostics_for_budget_result,
        ) as result_diagnostics,
        patch.object(
            evaluation_module,
            "diagnostics_for_budget_failure",
            wraps=evaluation_module.diagnostics_for_budget_failure,
        ) as failure_diagnostics,
    ):
        result = asyncio.run(evaluate_total_budget_diagnostics())

    assert result_diagnostics.call_count == 3
    assert failure_diagnostics.call_count == 4
    assert result.scenario_id == "total_budget_diagnostics"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "fit_reports_capacity_counts_and_exact_mode",
        "degraded_fit_aggregates_layers_tiers_and_estimate_mode",
        "bounded_failures_preserve_reason_and_reduction_counts",
        "diagnostics_surface_remains_content_free",
        "available_cognitive_capacity_clamps_at_zero",
        "mismatched_config_and_invalid_step_count_are_rejected",
    }
    assert {check.boundary for check in result.checks} == {"cognitive_budget"}
    assert result.metrics == {
        "result_diagnostics_call_count": 3,
        "failure_diagnostics_call_count": 4,
        "successful_outcome_count": 2,
        "bounded_failure_outcome_count": 3,
        "content_field_count": 0,
        "invalid_input_rejection_count": 2,
    }
