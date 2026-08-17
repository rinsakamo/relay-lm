from __future__ import annotations

from collections.abc import Callable

from relaylm.budget import TotalBudgetConfig
from relaylm.budget_enforcement import (
    SerializedInputTokenCount,
    TokenCountMode,
    evaluate_serialized_input_fit,
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


async def evaluate_serialized_input_fit_component() -> EvaluationScenarioResult:
    exact_count = SerializedInputTokenCount(
        total_input_tokens=80,
        required_input_framing_tokens=30,
        mode=TokenCountMode.EXACT,
    )
    conservative_count = SerializedInputTokenCount(
        total_input_tokens=90,
        required_input_framing_tokens=35,
        mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
    )

    config = TotalBudgetConfig(model_context_window=100, reserved_output_tokens=20)
    exact_fit = evaluate_serialized_input_fit(config=config, count=exact_count)
    overflow_fit = evaluate_serialized_input_fit(
        config=config,
        count=SerializedInputTokenCount(
            total_input_tokens=81,
            required_input_framing_tokens=30,
            mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
        ),
    )
    reserve_overflow_fit = evaluate_serialized_input_fit(
        config=TotalBudgetConfig(model_context_window=32, reserved_output_tokens=40),
        count=SerializedInputTokenCount(
            total_input_tokens=0,
            required_input_framing_tokens=0,
            mode=TokenCountMode.EXACT,
        ),
    )

    invalid_input_rejections = (
        _raises(
            ValueError,
            lambda: SerializedInputTokenCount(-1, 0, TokenCountMode.EXACT),
        ),
        _raises(
            TypeError,
            lambda: SerializedInputTokenCount(True, 0, TokenCountMode.EXACT),  # type: ignore[arg-type]
        ),
        _raises(
            ValueError,
            lambda: SerializedInputTokenCount(10, -1, TokenCountMode.EXACT),
        ),
        _raises(
            TypeError,
            lambda: SerializedInputTokenCount(10, False, TokenCountMode.EXACT),  # type: ignore[arg-type]
        ),
        _raises(
            ValueError,
            lambda: SerializedInputTokenCount(10, 11, TokenCountMode.EXACT),
        ),
        _raises(
            TypeError,
            lambda: SerializedInputTokenCount(10, 2, "estimate"),  # type: ignore[arg-type]
        ),
    )

    checks = (
        EvaluationCheck(
            check_id="exact_count_preserves_serialized_accounting",
            boundary="cognitive_budget",
            passed=(
                exact_count.cognitive_input_tokens == 50
                and exact_count.mode is TokenCountMode.EXACT
                and exact_count.mode.value == "exact"
            ),
            expected=50,
            observed=exact_count.cognitive_input_tokens,
        ),
        EvaluationCheck(
            check_id="conservative_estimate_is_explicit_mode",
            boundary="cognitive_budget",
            passed=(
                conservative_count.cognitive_input_tokens == 55
                and conservative_count.mode is TokenCountMode.CONSERVATIVE_ESTIMATE
                and conservative_count.mode.value == "conservative_estimate"
            ),
            expected="conservative_estimate",
            observed=conservative_count.mode.value,
        ),
        EvaluationCheck(
            check_id="final_serialized_count_controls_hard_fit",
            boundary="cognitive_budget",
            passed=(
                exact_fit.effective_input_capacity == 80
                and exact_fit.fits
                and exact_fit.overflow_tokens == 0
                and not overflow_fit.fits
                and overflow_fit.overflow_tokens == 1
            ),
            expected=1,
            observed=overflow_fit.overflow_tokens,
        ),
        EvaluationCheck(
            check_id="oversized_output_reserve_cannot_fit_empty_input",
            boundary="cognitive_budget",
            passed=(
                reserve_overflow_fit.effective_input_capacity == 0
                and not reserve_overflow_fit.fits
                and reserve_overflow_fit.overflow_tokens == 8
            ),
            expected=8,
            observed=reserve_overflow_fit.overflow_tokens,
        ),
        EvaluationCheck(
            check_id="invalid_counts_and_untyped_modes_are_rejected",
            boundary="cognitive_budget",
            passed=all(invalid_input_rejections),
            expected=6,
            observed=sum(invalid_input_rejections),
        ),
    )
    fits = (exact_fit, overflow_fit, reserve_overflow_fit)
    return EvaluationScenarioResult(
        scenario_id="serialized_input_fit",
        checks=checks,
        metrics={
            "fit_evaluation_count": len(fits),
            "count_mode_count": len(TokenCountMode),
            "fit_case_count": sum(fit.fits for fit in fits),
            "overflow_case_count": sum(not fit.fits for fit in fits),
            "invalid_input_rejection_count": sum(invalid_input_rejections),
        },
    )
