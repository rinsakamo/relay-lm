from __future__ import annotations

from collections.abc import Callable

from relaylm.budget import (
    ProtectedAnchorTokenCounts,
    TotalBudgetAccounting,
    TotalBudgetConfig,
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


async def evaluate_total_budget_accounting() -> EvaluationScenarioResult:
    normal = TotalBudgetAccounting(
        config=TotalBudgetConfig(
            model_context_window=100,
            reserved_output_tokens=20,
        ),
        protected=ProtectedAnchorTokenCounts(
            required_input_framing=10,
            identity=15,
            current_event=5,
        ),
    )
    protected_overflow = TotalBudgetAccounting(
        config=TotalBudgetConfig(
            model_context_window=40,
            reserved_output_tokens=10,
        ),
        protected=ProtectedAnchorTokenCounts(
            required_input_framing=10,
            identity=15,
            current_event=10,
        ),
    )
    reserve_overflow = TotalBudgetAccounting(
        config=TotalBudgetConfig(
            model_context_window=32,
            reserved_output_tokens=40,
        ),
        protected=ProtectedAnchorTokenCounts(
            required_input_framing=0,
            identity=0,
            current_event=0,
        ),
    )

    invalid_count_results = (
        _raises(
            ValueError,
            lambda: TotalBudgetConfig(
                model_context_window=0,
                reserved_output_tokens=0,
            ),
        ),
        _raises(
            TypeError,
            lambda: TotalBudgetConfig(
                model_context_window=True,
                reserved_output_tokens=0,
            ),
        ),
        _raises(
            ValueError,
            lambda: TotalBudgetConfig(
                model_context_window=100,
                reserved_output_tokens=-1,
            ),
        ),
        _raises(
            TypeError,
            lambda: ProtectedAnchorTokenCounts(
                required_input_framing=False,
                identity=0,
                current_event=0,
            ),
        ),
    )
    missing_argument_results = (
        _raises(TypeError, lambda: TotalBudgetConfig()),  # type: ignore[call-arg]
        _raises(TypeError, lambda: ProtectedAnchorTokenCounts()),  # type: ignore[call-arg]
    )

    checks = (
        EvaluationCheck(
            check_id="hard_capacity_equation_preserved",
            boundary="cognitive_budget",
            passed=(
                normal.config.serialized_input_capacity == 80
                and normal.remaining_after_output_reserve == 80
                and normal.remaining_after_framing == 70
                and normal.cognitive_input_capacity == 70
                and normal.protected.protected_cognitive_input_tokens == 20
                and normal.protected.protected_serialized_input_tokens == 30
                and normal.remaining_after_protected_anchors == 50
                and normal.degradable_cognitive_input_capacity == 50
                and normal.protected_floor_tokens == 50
                and normal.protected_floor_fits
                and normal.protected_floor_overflow_tokens == 0
            ),
            expected=50,
            observed=normal.degradable_cognitive_input_capacity,
        ),
        EvaluationCheck(
            check_id="protected_floor_overflow_exposed",
            boundary="cognitive_budget",
            passed=(
                protected_overflow.remaining_after_protected_anchors == -5
                and protected_overflow.degradable_cognitive_input_capacity == 0
                and protected_overflow.protected_floor_tokens == 45
                and not protected_overflow.protected_floor_fits
                and protected_overflow.protected_floor_overflow_tokens == 5
            ),
            expected=5,
            observed=protected_overflow.protected_floor_overflow_tokens,
        ),
        EvaluationCheck(
            check_id="output_reserve_overflow_exposed",
            boundary="cognitive_budget",
            passed=(
                reserve_overflow.config.serialized_input_capacity == 0
                and reserve_overflow.remaining_after_output_reserve == -8
                and reserve_overflow.cognitive_input_capacity == 0
                and not reserve_overflow.protected_floor_fits
                and reserve_overflow.protected_floor_overflow_tokens == 8
            ),
            expected=8,
            observed=reserve_overflow.protected_floor_overflow_tokens,
        ),
        EvaluationCheck(
            check_id="invalid_explicit_counts_rejected",
            boundary="cognitive_budget",
            passed=all(invalid_count_results),
            expected=4,
            observed=sum(invalid_count_results),
        ),
        EvaluationCheck(
            check_id="budget_types_require_explicit_counts",
            boundary="cognitive_budget",
            passed=all(missing_argument_results),
            expected=2,
            observed=sum(missing_argument_results),
        ),
    )
    accountings = (normal, protected_overflow, reserve_overflow)
    return EvaluationScenarioResult(
        scenario_id="total_budget_accounting",
        checks=checks,
        metrics={
            "accounting_fixture_count": len(accountings),
            "protected_floor_fit_count": sum(
                accounting.protected_floor_fits for accounting in accountings
            ),
            "overflow_fixture_count": sum(
                not accounting.protected_floor_fits for accounting in accountings
            ),
            "invalid_count_rejection_count": sum(invalid_count_results),
            "missing_argument_rejection_count": sum(missing_argument_results),
        },
    )
