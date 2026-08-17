from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_budget_owner_controls as evaluation_module
from relaylm.evaluation_budget_owner_controls import evaluate_budget_owner_controls


def test_budget_owner_controls_component_uses_real_translation_api() -> None:
    with patch.object(
        evaluation_module,
        "owner_controls_for_budget_plan",
        wraps=evaluation_module.owner_controls_for_budget_plan,
    ) as translate:
        result = asyncio.run(evaluate_budget_owner_controls())

    assert translate.call_count == 3
    assert result.scenario_id == "budget_owner_controls"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "plan_caps_translate_to_owner_parameter_units",
        "policy_floors_do_not_change_owner_controls",
        "continuity_selection_surface_is_not_introduced",
    }
    assert {check.boundary for check in result.checks} == {"cognitive_budget"}
    assert result.metrics == {
        "translation_call_count": 3,
        "context_compiler_control_count": 3,
        "retrieval_control_count": 4,
        "continuity_control_count": 0,
    }
