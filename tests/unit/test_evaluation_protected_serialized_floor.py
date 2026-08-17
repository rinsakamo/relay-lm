from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_protected_serialized_floor as evaluation_module
from relaylm.evaluation_protected_serialized_floor import (
    evaluate_protected_serialized_floor,
)


def test_protected_serialized_floor_component_uses_real_enforcement_apis() -> None:
    with (
        patch.object(
            evaluation_module,
            "enforce_protected_serialized_input_floor",
            wraps=evaluation_module.enforce_protected_serialized_input_floor,
        ) as direct_guard,
        patch.object(
            evaluation_module,
            "enforce_total_cognitive_budget",
            wraps=evaluation_module.enforce_total_cognitive_budget,
        ) as total_enforcement,
    ):
        result = asyncio.run(evaluate_protected_serialized_floor())

    assert direct_guard.call_count == 3
    assert total_enforcement.call_count == 3
    assert result.scenario_id == "protected_serialized_floor"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "protected_overflow_stops_before_full_plan_compilation",
        "protected_fit_precedes_full_serialized_enforcement",
        "direct_guard_returns_authoritative_count",
        "protected_failure_metadata_is_content_free",
        "invalid_protected_projection_and_counter_results_are_rejected",
    }
    assert {check.boundary for check in result.checks} == {"cognitive_budget"}
    assert result.metrics == {
        "direct_guard_call_count": 3,
        "total_enforcement_call_count": 3,
        "protected_overflow_count": 1,
        "full_compile_after_protected_overflow_count": 0,
        "invalid_input_rejection_count": 3,
    }
