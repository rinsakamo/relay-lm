from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_cognitive_budget_turn_wiring as evaluation_module
from relaylm.evaluation_cognitive_budget_turn_wiring import (
    evaluate_cognitive_budget_turn_wiring,
)


def test_cognitive_budget_turn_wiring_component_uses_real_turn_apis() -> None:
    with (
        patch.object(
            evaluation_module,
            "run_user_turn",
            wraps=evaluation_module.run_user_turn,
        ) as buffered,
        patch.object(
            evaluation_module,
            "run_user_turn_streaming",
            wraps=evaluation_module.run_user_turn_streaming,
        ) as streaming,
    ):
        result = asyncio.run(evaluate_cognitive_budget_turn_wiring())

    assert buffered.call_count == 5
    assert streaming.call_count == 1
    assert result.scenario_id == "cognitive_budget_turn_wiring"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "buffered_generation_occurs_once_after_fit",
        "budget_pressure_recompiles_before_single_generation",
        "protected_floor_failure_precedes_generation",
        "degradation_exhaustion_precedes_generation",
        "legacy_retrieval_budget_is_rejected_before_event_append",
        "streaming_generation_occurs_once_after_fit",
    }
    assert {check.boundary for check in result.checks} == {"turn_runtime"}
    assert result.metrics == {
        "ordinary_turn_call_count": 6,
        "buffered_turn_call_count": 5,
        "streaming_turn_call_count": 1,
        "provider_generation_count": 3,
        "budget_failure_before_generation_count": 2,
        "pre_event_configuration_rejection_count": 1,
    }
