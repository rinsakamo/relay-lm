from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_cognitive_budget_turn_diagnostics as evaluation_module
from relaylm.evaluation_cognitive_budget_turn_diagnostics import (
    evaluate_cognitive_budget_turn_diagnostics,
)


def test_cognitive_budget_turn_diagnostics_component_uses_real_turn_apis() -> None:
    with (
        patch.object(
            evaluation_module,
            "run_user_turn_with_cognitive_budget_diagnostics",
            wraps=evaluation_module.run_user_turn_with_cognitive_budget_diagnostics,
        ) as buffered,
        patch.object(
            evaluation_module,
            "run_user_turn_streaming_with_cognitive_budget_diagnostics",
            wraps=evaluation_module.run_user_turn_streaming_with_cognitive_budget_diagnostics,
        ) as streaming,
    ):
        result = asyncio.run(evaluate_cognitive_budget_turn_diagnostics())

    assert buffered.call_count == 4
    assert streaming.call_count == 1
    assert result.scenario_id == "cognitive_budget_turn_diagnostics"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "buffered_fit_returns_content_free_diagnostics_after_one_generation",
        "buffered_pressure_returns_degraded_fit_counts",
        "protected_failure_preserves_failure_family_and_content_free_diagnostics",
        "degradation_failure_exposes_reduction_counts_before_generation",
        "streaming_fit_returns_diagnostics_after_one_stream_generation",
    }
    assert {check.boundary for check in result.checks} == {"turn_runtime"}
    assert result.metrics == {
        "diagnostic_turn_call_count": 5,
        "buffered_diagnostic_turn_call_count": 4,
        "streaming_diagnostic_turn_call_count": 1,
        "provider_generation_count": 3,
        "bounded_failure_count": 2,
        "fit_outcome_count": 2,
        "degraded_fit_outcome_count": 1,
    }
