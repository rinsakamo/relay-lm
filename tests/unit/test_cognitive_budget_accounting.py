from __future__ import annotations

import pytest

from relaylm.budget import (
    ProtectedAnchorTokenCounts,
    TotalBudgetAccounting,
    TotalBudgetConfig,
)


def test_total_budget_accounting_preserves_hard_capacity_equation() -> None:
    accounting = TotalBudgetAccounting(
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

    assert accounting.config.serialized_input_capacity == 80
    assert accounting.remaining_after_output_reserve == 80
    assert accounting.remaining_after_framing == 70
    assert accounting.cognitive_input_capacity == 70
    assert accounting.protected.protected_cognitive_input_tokens == 20
    assert accounting.protected.protected_serialized_input_tokens == 30
    assert accounting.remaining_after_protected_anchors == 50
    assert accounting.degradable_cognitive_input_capacity == 50
    assert accounting.protected_floor_tokens == 50
    assert accounting.protected_floor_fits is True
    assert accounting.protected_floor_overflow_tokens == 0


def test_total_budget_accounting_exposes_impossible_protected_floor() -> None:
    accounting = TotalBudgetAccounting(
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

    assert accounting.remaining_after_protected_anchors == -5
    assert accounting.degradable_cognitive_input_capacity == 0
    assert accounting.protected_floor_tokens == 45
    assert accounting.protected_floor_fits is False
    assert accounting.protected_floor_overflow_tokens == 5


def test_total_budget_accounting_exposes_output_reserve_larger_than_window() -> None:
    accounting = TotalBudgetAccounting(
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

    assert accounting.config.serialized_input_capacity == 0
    assert accounting.remaining_after_output_reserve == -8
    assert accounting.cognitive_input_capacity == 0
    assert accounting.protected_floor_fits is False
    assert accounting.protected_floor_overflow_tokens == 8


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("model_context_window", 0, ValueError),
        ("model_context_window", True, TypeError),
        ("reserved_output_tokens", -1, ValueError),
        ("reserved_output_tokens", 1.5, TypeError),
    ],
)
def test_total_budget_config_rejects_invalid_explicit_counts(
    field: str,
    value: object,
    error: type[Exception],
) -> None:
    values = {
        "model_context_window": 100,
        "reserved_output_tokens": 20,
    }
    values[field] = value

    with pytest.raises(error):
        TotalBudgetConfig(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("required_input_framing", -1, ValueError),
        ("required_input_framing", False, TypeError),
        ("identity", -1, ValueError),
        ("identity", 2.5, TypeError),
        ("current_event", -1, ValueError),
        ("current_event", True, TypeError),
    ],
)
def test_protected_anchor_counts_reject_invalid_explicit_counts(
    field: str,
    value: object,
    error: type[Exception],
) -> None:
    values = {
        "required_input_framing": 10,
        "identity": 15,
        "current_event": 5,
    }
    values[field] = value

    with pytest.raises(error):
        ProtectedAnchorTokenCounts(**values)  # type: ignore[arg-type]


def test_budget_types_define_no_numeric_defaults() -> None:
    with pytest.raises(TypeError):
        TotalBudgetConfig()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        ProtectedAnchorTokenCounts()  # type: ignore[call-arg]
