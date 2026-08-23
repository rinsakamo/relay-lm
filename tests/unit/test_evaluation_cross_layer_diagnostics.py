from __future__ import annotations

import asyncio

from relaylm.evaluation_cross_layer import evaluate_cross_layer_context_diagnostics


def test_cross_layer_context_diagnostics_evaluation_is_registered() -> None:
    result = asyncio.run(evaluate_cross_layer_context_diagnostics())

    assert result.scenario_id == "cross_layer_context_diagnostics"
    assert result.status == "pass"
    assert all(check.passed for check in result.checks)
    assert {check.boundary for check in result.checks} == {
        "context_compiler",
        "diagnostics",
    }
    assert result.metrics == {
        "diagnostic_layer_count": 4,
        "memory_authority_suppressed_count": 1,
        "event_current_excluded_count": 1,
        "event_redundancy_overlap_count": 1,
    }
