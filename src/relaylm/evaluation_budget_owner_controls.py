from __future__ import annotations

import dataclasses

from relaylm.budget import BudgetPlan, CountCharacterEnvelope, CountEnvelope
from relaylm.budget_controls import owner_controls_for_budget_plan
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult


def _plan(*, state_floor: int = 1) -> BudgetPlan:
    return BudgetPlan(
        canonical_state=CountEnvelope(max_items=7, floor_items=state_floor),
        working_context=CountCharacterEnvelope(
            max_items=5,
            floor_items=1,
            max_chars=900,
            floor_chars=100,
        ),
        retrieved_memory=CountCharacterEnvelope(
            max_items=3,
            floor_items=0,
            max_chars=700,
            floor_chars=0,
        ),
        event_evidence=CountCharacterEnvelope(
            max_items=2,
            floor_items=0,
            max_chars=500,
            floor_chars=0,
        ),
    )


async def evaluate_budget_owner_controls() -> EvaluationScenarioResult:
    controls = owner_controls_for_budget_plan(_plan())
    low_floor = owner_controls_for_budget_plan(_plan(state_floor=1))
    high_floor = owner_controls_for_budget_plan(_plan(state_floor=4))

    context_fields = {field.name for field in dataclasses.fields(controls.context_compiler)}
    retrieval_fields = {field.name for field in dataclasses.fields(controls.retrieval)}
    all_control_fields = context_fields | retrieval_fields

    checks = (
        EvaluationCheck(
            check_id="plan_caps_translate_to_owner_parameter_units",
            boundary="cognitive_budget",
            passed=(
                controls.context_compiler.max_state_records == 7
                and controls.context_compiler.max_working_context_events == 5
                and controls.context_compiler.max_working_context_chars == 900
                and controls.retrieval.memory_max_chunks == 3
                and controls.retrieval.memory_max_chars == 700
                and controls.retrieval.event_max_events == 2
                and controls.retrieval.event_max_chars == 500
            ),
            expected=7,
            observed=len(context_fields) + len(retrieval_fields),
        ),
        EvaluationCheck(
            check_id="policy_floors_do_not_change_owner_controls",
            boundary="cognitive_budget",
            passed=low_floor == high_floor,
            expected=True,
            observed=low_floor == high_floor,
        ),
        EvaluationCheck(
            check_id="continuity_selection_surface_is_not_introduced",
            boundary="cognitive_budget",
            passed=all("continuity" not in name for name in all_control_fields),
            expected=0,
            observed=sum("continuity" in name for name in all_control_fields),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="budget_owner_controls",
        checks=checks,
        metrics={
            "translation_call_count": 3,
            "context_compiler_control_count": len(context_fields),
            "retrieval_control_count": len(retrieval_fields),
            "continuity_control_count": sum(
                "continuity" in name for name in all_control_fields
            ),
        },
    )
