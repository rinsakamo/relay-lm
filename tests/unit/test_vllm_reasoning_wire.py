from __future__ import annotations

import pytest

from relaylm.providers.vllm_reasoning import (
    VLLM_REASONING_EFFORT_VALUES,
    VLLMReasoningWireControls,
)


def test_vllm_reasoning_wire_uses_exact_chat_completions_field_names() -> None:
    controls = VLLMReasoningWireControls(
        reasoning_effort="none",
        thinking_token_budget=768,
    )

    assert controls.to_mapping() == {
        "reasoning_effort": "none",
        "thinking_token_budget": 768,
    }
    assert controls.wire_fields == (
        ("reasoning_effort", "none"),
        ("thinking_token_budget", 768),
    )


def test_vllm_reasoning_wire_has_no_hidden_defaults() -> None:
    controls = VLLMReasoningWireControls()

    assert controls.to_mapping() == {}
    assert controls.wire_fields == ()


def test_vllm_reasoning_effort_vocabulary_matches_current_public_protocol() -> None:
    assert VLLM_REASONING_EFFORT_VALUES == (
        "high",
        "low",
        "max",
        "medium",
        "minimal",
        "none",
        "xhigh",
    )
    for effort in VLLM_REASONING_EFFORT_VALUES:
        assert VLLMReasoningWireControls(reasoning_effort=effort).to_mapping() == {
            "reasoning_effort": effort
        }


def test_vllm_wire_does_not_accept_relaylm_semantic_mode_spelling() -> None:
    with pytest.raises(ValueError, match="unsupported vLLM reasoning_effort"):
        VLLMReasoningWireControls(reasoning_effort="off")
    with pytest.raises(ValueError, match="unsupported vLLM reasoning_effort"):
        VLLMReasoningWireControls(reasoning_effort="bounded")


def test_vllm_reasoning_budget_is_explicit_positive_integer_only() -> None:
    for value in (0, -1, -2):
        with pytest.raises(ValueError, match="thinking_token_budget must be positive"):
            VLLMReasoningWireControls(thinking_token_budget=value)
    for value in (True, 1.5, "768"):
        with pytest.raises(TypeError, match="thinking_token_budget must be an integer"):
            VLLMReasoningWireControls(thinking_token_budget=value)  # type: ignore[arg-type]


def test_vllm_reasoning_wire_rejects_invalid_effort_type_or_empty_value() -> None:
    with pytest.raises(TypeError, match="reasoning_effort must be a string"):
        VLLMReasoningWireControls(reasoning_effort=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="reasoning_effort must not be empty"):
        VLLMReasoningWireControls(reasoning_effort="   ")
