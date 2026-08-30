from __future__ import annotations

import dataclasses
from collections.abc import Callable

from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetDegradationStep,
    BudgetLayer,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
)
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult


def _raises(error: type[Exception], action: Callable[[], object]) -> bool:
    try:
        action()
    except error:
        return True
    except Exception:
        return False
    return False


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
        package_knowledge=CountCharacterEnvelope(
            max_items=2,
            floor_items=0,
            max_chars=400,
            floor_chars=0,
        ),
    )


async def evaluate_budget_degradation_plan() -> EvaluationScenarioResult:
    managed_fields = {field.name for field in dataclasses.fields(BudgetPlan)}
    initial = _plan()
    full_policy = BudgetDegradationPolicy(
        initial_plan=initial,
        steps=(
            BudgetDegradationStep(
                BudgetLayer.RETRIEVED_MEMORY,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.PACKAGE_KNOWLEDGE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.WORKING_CONTEXT,
                CountCharacterEnvelope(1, 1, 200, 200),
            ),
            BudgetDegradationStep(
                BudgetLayer.CANONICAL_STATE,
                CountEnvelope(2, 2),
            ),
        ),
    )
    after_three = full_policy.plan_after_steps(3)
    after_four = full_policy.plan_after_steps(4)
    final = full_policy.final_plan

    memory_first = BudgetDegradationPolicy(
        initial_plan=initial,
        steps=(
            BudgetDegradationStep(
                BudgetLayer.RETRIEVED_MEMORY,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.PACKAGE_KNOWLEDGE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
        ),
    )
    event_first = BudgetDegradationPolicy(
        initial_plan=initial,
        steps=(
            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.RETRIEVED_MEMORY,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.PACKAGE_KNOWLEDGE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
        ),
    )
    knowledge_first = BudgetDegradationPolicy(
        initial_plan=initial,
        steps=(
            BudgetDegradationStep(
                BudgetLayer.PACKAGE_KNOWLEDGE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.RETRIEVED_MEMORY,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
            BudgetDegradationStep(
                BudgetLayer.EVENT_EVIDENCE,
                CountCharacterEnvelope(0, 0, 0, 0),
            ),
        ),
    )

    reverse_initial = BudgetPlan(
        canonical_state=CountEnvelope(4, 1),
        working_context=CountCharacterEnvelope(2, 0, 100, 0),
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )
    monotonic_initial = BudgetPlan(
        canonical_state=CountEnvelope(4, 1),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(2, 0, 100, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )
    policy_rejections = (
        _raises(
            ValueError,
            lambda: BudgetDegradationPolicy(
                initial_plan=_plan(),
                steps=(
                    BudgetDegradationStep(
                        BudgetLayer.WORKING_CONTEXT,
                        CountCharacterEnvelope(1, 1, 200, 200),
                    ),
                ),
            ),
        ),
        _raises(
            ValueError,
            lambda: BudgetDegradationPolicy(
                initial_plan=_plan(),
                steps=(
                    BudgetDegradationStep(
                        BudgetLayer.RETRIEVED_MEMORY,
                        CountCharacterEnvelope(0, 0, 0, 0),
                    ),
                    BudgetDegradationStep(
                        BudgetLayer.EVENT_EVIDENCE,
                        CountCharacterEnvelope(0, 0, 0, 0),
                    ),
                    BudgetDegradationStep(
                        BudgetLayer.CANONICAL_STATE,
                        CountEnvelope(2, 2),
                    ),
                ),
            ),
        ),
        _raises(
            ValueError,
            lambda: BudgetDegradationPolicy(
                initial_plan=reverse_initial,
                steps=(
                    BudgetDegradationStep(
                        BudgetLayer.WORKING_CONTEXT,
                        CountCharacterEnvelope(0, 0, 0, 0),
                    ),
                    BudgetDegradationStep(
                        BudgetLayer.RETRIEVED_MEMORY,
                        CountCharacterEnvelope(0, 0, 0, 0),
                    ),
                ),
            ),
        ),
        _raises(
            ValueError,
            lambda: BudgetDegradationPolicy(
                initial_plan=monotonic_initial,
                steps=(
                    BudgetDegradationStep(
                        BudgetLayer.RETRIEVED_MEMORY,
                        CountCharacterEnvelope(3, 0, 100, 0),
                    ),
                ),
            ),
        ),
        _raises(
            ValueError,
            lambda: BudgetDegradationPolicy(
                initial_plan=monotonic_initial,
                steps=(
                    BudgetDegradationStep(
                        BudgetLayer.RETRIEVED_MEMORY,
                        CountCharacterEnvelope(2, 0, 100, 0),
                    ),
                ),
            ),
        ),
        _raises(
            ValueError,
            lambda: BudgetDegradationPolicy(
                initial_plan=monotonic_initial,
                steps=(
                    BudgetDegradationStep(
                        BudgetLayer.RETRIEVED_MEMORY,
                        CountCharacterEnvelope(1, 1, 50, 0),
                    ),
                ),
            ),
        ),
    )

    empty_policy = BudgetDegradationPolicy(initial_plan=_plan(), steps=())
    input_validation_rejections = (
        _raises(ValueError, lambda: CountEnvelope(max_items=1, floor_items=2)),
        _raises(
            ValueError,
            lambda: CountCharacterEnvelope(
                max_items=1,
                floor_items=0,
                max_chars=10,
                floor_chars=11,
            ),
        ),
        _raises(TypeError, lambda: CountEnvelope(max_items=True, floor_items=0)),
        _raises(TypeError, lambda: CountEnvelope()),  # type: ignore[call-arg]
        _raises(TypeError, lambda: CountCharacterEnvelope()),  # type: ignore[call-arg]
        _raises(ValueError, lambda: empty_policy.plan_after_steps(1)),
        _raises(TypeError, lambda: empty_policy.plan_after_steps(True)),  # type: ignore[arg-type]
    )

    checks = (
        EvaluationCheck(
            check_id="plan_scope_omits_unowned_continuity_pressure",
            boundary="cognitive_budget",
            passed=(
                managed_fields
                == {
                    "canonical_state",
                    "working_context",
                    "retrieved_memory",
                    "event_evidence",
                    "package_knowledge",
                }
                and "continuity" not in managed_fields
            ),
            expected=5,
            observed=len(managed_fields),
        ),
        EvaluationCheck(
            check_id="tier_order_reaches_configured_floors",
            boundary="cognitive_budget",
            passed=(
                full_policy.plan_after_steps(0) == initial
                and after_three.retrieved_memory.at_floor
                and after_three.event_evidence.at_floor
                and after_three.package_knowledge.at_floor
                and after_four.working_context.at_floor
                and final.canonical_state.at_floor
            ),
            expected=True,
            observed=final.canonical_state.at_floor,
        ),
        EvaluationCheck(
            check_id="tier3_order_remains_caller_controlled",
            boundary="cognitive_budget",
            passed=(
                memory_first.plan_after_steps(1).retrieved_memory.at_floor
                and not memory_first.plan_after_steps(1).event_evidence.at_floor
                and not memory_first.plan_after_steps(1).package_knowledge.at_floor
                and event_first.plan_after_steps(1).event_evidence.at_floor
                and not event_first.plan_after_steps(1).retrieved_memory.at_floor
                and not event_first.plan_after_steps(1).package_knowledge.at_floor
                and knowledge_first.plan_after_steps(1).package_knowledge.at_floor
                and not knowledge_first.plan_after_steps(1).retrieved_memory.at_floor
                and not knowledge_first.plan_after_steps(1).event_evidence.at_floor
                and memory_first.final_plan == event_first.final_plan
                and event_first.final_plan == knowledge_first.final_plan
            ),
            expected=True,
            observed=(
                memory_first.final_plan == event_first.final_plan
                and event_first.final_plan == knowledge_first.final_plan
            ),
        ),
        EvaluationCheck(
            check_id="tier2_before_tier3_floor_is_rejected",
            boundary="cognitive_budget",
            passed=policy_rejections[0],
            expected=True,
            observed=policy_rejections[0],
        ),
        EvaluationCheck(
            check_id="tier1_before_tier2_floor_is_rejected",
            boundary="cognitive_budget",
            passed=policy_rejections[1],
            expected=True,
            observed=policy_rejections[1],
        ),
        EvaluationCheck(
            check_id="return_to_lower_protection_tier_is_rejected",
            boundary="cognitive_budget",
            passed=policy_rejections[2],
            expected=True,
            observed=policy_rejections[2],
        ),
        EvaluationCheck(
            check_id="non_monotonic_or_floor_changing_steps_are_rejected",
            boundary="cognitive_budget",
            passed=all(policy_rejections[3:]),
            expected=3,
            observed=sum(policy_rejections[3:]),
        ),
        EvaluationCheck(
            check_id="envelope_and_step_count_inputs_are_explicitly_validated",
            boundary="cognitive_budget",
            passed=all(input_validation_rejections),
            expected=7,
            observed=sum(input_validation_rejections),
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="budget_degradation_plan",
        checks=checks,
        metrics={
            "managed_layer_count": len(managed_fields),
            "full_plan_step_count": len(full_policy.steps),
            "tier3_order_variant_count": 3,
            "policy_rejection_count": sum(policy_rejections),
            "input_validation_rejection_count": sum(input_validation_rejections),
        },
    )
