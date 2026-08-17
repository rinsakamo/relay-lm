from __future__ import annotations

import pytest

from relaylm.budget import TotalBudgetConfig
from relaylm.budget_enforcement import (
    SerializedInputTokenCount,
    TokenCountMode,
    evaluate_serialized_input_fit,
)


def test_exact_serialized_count_preserves_framing_and_cognitive_accounting() -> None:
    count = SerializedInputTokenCount(
        total_input_tokens=80,
        required_input_framing_tokens=30,
        mode=TokenCountMode.EXACT,
    )

    assert count.cognitive_input_tokens == 50
    assert count.mode.value == "exact"


def test_conservative_estimate_is_an_explicit_counting_mode() -> None:
    count = SerializedInputTokenCount(
        total_input_tokens=90,
        required_input_framing_tokens=35,
        mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
    )

    assert count.cognitive_input_tokens == 55
    assert count.mode.value == "conservative_estimate"


def test_final_serialized_count_is_authoritative_for_hard_fit() -> None:
    config = TotalBudgetConfig(
        model_context_window=100,
        reserved_output_tokens=20,
    )

    exact_fit = evaluate_serialized_input_fit(
        config=config,
        count=SerializedInputTokenCount(
            total_input_tokens=80,
            required_input_framing_tokens=30,
            mode=TokenCountMode.EXACT,
        ),
    )
    overflow = evaluate_serialized_input_fit(
        config=config,
        count=SerializedInputTokenCount(
            total_input_tokens=81,
            required_input_framing_tokens=30,
            mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
        ),
    )

    assert exact_fit.effective_input_capacity == 80
    assert exact_fit.fits is True
    assert exact_fit.overflow_tokens == 0
    assert overflow.fits is False
    assert overflow.overflow_tokens == 1


def test_output_reserve_larger_than_window_cannot_fit_even_empty_input() -> None:
    fit = evaluate_serialized_input_fit(
        config=TotalBudgetConfig(
            model_context_window=32,
            reserved_output_tokens=40,
        ),
        count=SerializedInputTokenCount(
            total_input_tokens=0,
            required_input_framing_tokens=0,
            mode=TokenCountMode.EXACT,
        ),
    )

    assert fit.effective_input_capacity == 0
    assert fit.fits is False
    assert fit.overflow_tokens == 8


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("total_input_tokens", -1, ValueError),
        ("total_input_tokens", True, TypeError),
        ("required_input_framing_tokens", -1, ValueError),
        ("required_input_framing_tokens", False, TypeError),
    ],
)
def test_serialized_count_rejects_invalid_counts(
    field: str,
    value: object,
    error: type[Exception],
) -> None:
    values = {
        "total_input_tokens": 10,
        "required_input_framing_tokens": 2,
        "mode": TokenCountMode.EXACT,
    }
    values[field] = value

    with pytest.raises(error):
        SerializedInputTokenCount(**values)  # type: ignore[arg-type]


def test_serialized_count_rejects_framing_larger_than_total() -> None:
    with pytest.raises(ValueError, match="must not exceed"):
        SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=11,
            mode=TokenCountMode.EXACT,
        )


def test_serialized_count_rejects_untyped_estimation_mode() -> None:
    with pytest.raises(TypeError, match="TokenCountMode"):
        SerializedInputTokenCount(
            total_input_tokens=10,
            required_input_framing_tokens=2,
            mode="estimate",  # type: ignore[arg-type]
        )
