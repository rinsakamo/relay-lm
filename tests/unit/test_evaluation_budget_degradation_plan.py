from __future__ import annotations

import asyncio

from relaylm.evaluation_budget_degradation_plan import (
    evaluate_budget_degradation_plan,
)


def test_budget_degradation_plan_component() -> None:
    result = asyncio.run(evaluate_budget_degradation_plan())

    assert result.scenario_id == "budget_degradation_plan"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "plan_scope_omits_unowned_continuity_pressure",
        "tier_order_reaches_configured_floors",
        "tier3_order_remains_caller_controlled",
        "tier2_before_tier3_floor_is_rejected",
        "tier1_before_tier2_floor_is_rejected",
        "return_to_lower_protection_tier_is_rejected",
        "non_monotonic_or_floor_changing_steps_are_rejected",
        "envelope_and_step_count_inputs_are_explicitly_validated",
    }
    assert {check.boundary for check in result.checks} == {"cognitive_budget"}
    assert result.metrics == {
        "managed_layer_count": 5,
        "full_plan_step_count": 5,
        "tier3_order_variant_count": 3,
        "policy_rejection_count": 6,
        "input_validation_rejection_count": 7,
    }
