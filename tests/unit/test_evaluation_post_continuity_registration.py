from __future__ import annotations

import asyncio

from relaylm.evaluation import (
    evaluate_budget_degradation_plan,
    evaluate_budget_owner_controls,
    evaluate_continuity_cognition_wiring,
    evaluate_freeform_current_state_shadow,
    evaluate_openai_serialized_counter,
    evaluate_protected_serialized_floor,
    evaluate_serialized_fit_enforcement,
    evaluate_serialized_input_fit,
    evaluate_total_budget_accounting,
)


def test_merged_post_continuity_evaluation_components_are_registered() -> None:
    results = tuple(
        asyncio.run(evaluate())
        for evaluate in (
            evaluate_continuity_cognition_wiring,
            evaluate_freeform_current_state_shadow,
            evaluate_total_budget_accounting,
            evaluate_budget_degradation_plan,
            evaluate_budget_owner_controls,
            evaluate_serialized_input_fit,
            evaluate_openai_serialized_counter,
            evaluate_serialized_fit_enforcement,
            evaluate_protected_serialized_floor,
        )
    )

    assert tuple(result.scenario_id for result in results) == (
        "continuity_cognition_wiring",
        "freeform_current_state_shadow",
        "total_budget_accounting",
        "budget_degradation_plan",
        "budget_owner_controls",
        "serialized_input_fit",
        "openai_serialized_counter",
        "serialized_fit_enforcement",
        "protected_serialized_floor",
    )
    assert all(result.status == "pass" for result in results)
