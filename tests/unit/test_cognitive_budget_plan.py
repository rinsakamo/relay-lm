from __future__ import annotations

import dataclasses

import pytest

from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetDegradationStep,
    BudgetLayer,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
)


def _plan() -> BudgetPlan:
    return BudgetPlan(
        canonical_state=CountEnvelope(max_items=8, floor_items=2),
        working_context=CountCharacterEnvelope(
            max_items=6,
            floor_items=1,
            max_chars=1200,
            floor_chars=200,
        ),
        retrieved_memory=CountCharacterEnvelope(
            max_items=4,
            floor_items=0,
            max_chars=800,
            floor_chars=0,
        ),
        event_evidence=CountCharacterEnvelope(
            max_items=3,
            floor_items=0,
            max_chars=600,
            floor_chars=0,
        ),
    )


def test_budget_plan_maps_only_existing_owner_control_layers() -> None:
    fields = {field.name for field in dataclasses.fields(BudgetPlan)}
    assert fields == {
        "canonical_state",
        "working_context",
        "retrieved_memory",
        "event_evidence",
        "package_knowledge",
    }
    assert "continuity" not in fields


def test_policy_allows_explicit_tier_3_then_tier_2_then_tier_1_reductions() -> None:
    initial = _plan()
    policy = BudgetDegradationPolicy(
        initial_plan=initial,
        steps=(
            BudgetDegradationStep(BudgetLayer.RETRIEVED_MEMORY, CountCharacterEnvelope(0, 0, 0, 0)),
            BudgetDegradationStep(BudgetLayer.EVENT_EVIDENCE, CountCharacterEnvelope(0, 0, 0, 0)),
            BudgetDegradationStep(BudgetLayer.WORKING_CONTEXT, CountCharacterEnvelope(1, 1, 200, 200)),
            BudgetDegradationStep(BudgetLayer.CANONICAL_STATE, CountEnvelope(2, 2)),
        ),
    )
    assert policy.plan_after_steps(0) == initial
    assert policy.plan_after_steps(2).retrieved_memory.at_floor is True
    assert policy.plan_after_steps(2).event_evidence.at_floor is True
    assert policy.plan_after_steps(3).working_context.at_floor is True
    assert policy.final_plan.canonical_state.at_floor is True


def test_policy_keeps_within_tier_order_explicit_and_deterministic() -> None:
    initial = _plan()
    first_memory = BudgetDegradationPolicy(
        initial,
        (
            BudgetDegradationStep(BudgetLayer.RETRIEVED_MEMORY, CountCharacterEnvelope(0, 0, 0, 0)),
            BudgetDegradationStep(BudgetLayer.EVENT_EVIDENCE, CountCharacterEnvelope(0, 0, 0, 0)),
        ),
    )
    first_event = BudgetDegradationPolicy(
        initial,
        (
            BudgetDegradationStep(BudgetLayer.EVENT_EVIDENCE, CountCharacterEnvelope(0, 0, 0, 0)),
            BudgetDegradationStep(BudgetLayer.RETRIEVED_MEMORY, CountCharacterEnvelope(0, 0, 0, 0)),
        ),
    )
    assert first_memory.plan_after_steps(1).retrieved_memory.at_floor is True
    assert first_memory.plan_after_steps(1).event_evidence.at_floor is False
    assert first_event.plan_after_steps(1).event_evidence.at_floor is True
    assert first_event.plan_after_steps(1).retrieved_memory.at_floor is False
    assert first_memory.final_plan == first_event.final_plan


def test_policy_rejects_tier_2_before_all_tier_3_layers_reach_floor() -> None:
    with pytest.raises(ValueError, match="lower-protection tiers reach floors"):
        BudgetDegradationPolicy(
            _plan(),
            (BudgetDegradationStep(BudgetLayer.WORKING_CONTEXT, CountCharacterEnvelope(1, 1, 200, 200)),),
        )


def test_policy_rejects_tier_1_before_working_context_reaches_floor() -> None:
    with pytest.raises(ValueError, match="lower-protection tiers reach floors"):
        BudgetDegradationPolicy(
            _plan(),
            (
                BudgetDegradationStep(BudgetLayer.RETRIEVED_MEMORY, CountCharacterEnvelope(0, 0, 0, 0)),
                BudgetDegradationStep(BudgetLayer.EVENT_EVIDENCE, CountCharacterEnvelope(0, 0, 0, 0)),
                BudgetDegradationStep(BudgetLayer.CANONICAL_STATE, CountEnvelope(2, 2)),
            ),
        )


def test_policy_rejects_return_to_lower_protection_tier() -> None:
    initial = BudgetPlan(
        canonical_state=CountEnvelope(4, 1),
        working_context=CountCharacterEnvelope(2, 0, 100, 0),
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )
    with pytest.raises(ValueError, match="cannot return"):
        BudgetDegradationPolicy(
            initial,
            (
                BudgetDegradationStep(BudgetLayer.WORKING_CONTEXT, CountCharacterEnvelope(0, 0, 0, 0)),
                BudgetDegradationStep(BudgetLayer.RETRIEVED_MEMORY, CountCharacterEnvelope(0, 0, 0, 0)),
            ),
        )


def test_policy_rejects_expansion_noop_and_floor_redefinition() -> None:
    initial = BudgetPlan(
        canonical_state=CountEnvelope(4, 1),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(2, 0, 100, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )
    with pytest.raises(ValueError, match="must not expand"):
        BudgetDegradationPolicy(
            initial,
            (BudgetDegradationStep(BudgetLayer.RETRIEVED_MEMORY, CountCharacterEnvelope(3, 0, 100, 0)),),
        )
    with pytest.raises(ValueError, match="strictly reduce"):
        BudgetDegradationPolicy(
            initial,
            (BudgetDegradationStep(BudgetLayer.RETRIEVED_MEMORY, CountCharacterEnvelope(2, 0, 100, 0)),),
        )
    with pytest.raises(ValueError, match="preserve configured layer floors"):
        BudgetDegradationPolicy(
            initial,
            (BudgetDegradationStep(BudgetLayer.RETRIEVED_MEMORY, CountCharacterEnvelope(1, 1, 50, 0)),),
        )


def test_envelopes_reject_invalid_bounds_without_defining_defaults() -> None:
    with pytest.raises(ValueError):
        CountEnvelope(max_items=1, floor_items=2)
    with pytest.raises(ValueError):
        CountCharacterEnvelope(max_items=1, floor_items=0, max_chars=10, floor_chars=11)
    with pytest.raises(TypeError):
        CountEnvelope(max_items=True, floor_items=0)
    with pytest.raises(TypeError):
        CountEnvelope()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        CountCharacterEnvelope()  # type: ignore[call-arg]


def test_plan_after_steps_rejects_out_of_range_count() -> None:
    policy = BudgetDegradationPolicy(initial_plan=_plan(), steps=())
    with pytest.raises(ValueError):
        policy.plan_after_steps(1)
    with pytest.raises(TypeError):
        policy.plan_after_steps(True)  # type: ignore[arg-type]
