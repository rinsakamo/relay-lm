from __future__ import annotations

import dataclasses

from relaylm.budget import BudgetPlan, CountCharacterEnvelope, CountEnvelope
from relaylm.budget_controls import owner_controls_for_budget_plan


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


def test_budget_plan_translates_to_existing_owner_parameter_units() -> None:
    controls = owner_controls_for_budget_plan(_plan())

    assert controls.context_compiler.max_state_records == 7
    assert controls.context_compiler.max_working_context_events == 5
    assert controls.context_compiler.max_working_context_chars == 900
    assert controls.retrieval.memory_max_chunks == 3
    assert controls.retrieval.memory_max_chars == 700
    assert controls.retrieval.event_max_events == 2
    assert controls.retrieval.event_max_chars == 500


def test_owner_controls_carry_current_caps_not_policy_floors() -> None:
    first = owner_controls_for_budget_plan(_plan(state_floor=1))
    second = owner_controls_for_budget_plan(_plan(state_floor=4))

    assert first == second


def test_owner_control_translation_defines_no_continuity_selection_surface() -> None:
    controls = owner_controls_for_budget_plan(_plan())
    names = {
        field.name
        for container in (
            controls,
            controls.context_compiler,
            controls.retrieval,
        )
        for field in dataclasses.fields(container)
    }

    assert all("continuity" not in name for name in names)
