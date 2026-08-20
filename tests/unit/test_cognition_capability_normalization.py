from __future__ import annotations

import pytest

from relaylm.cognition_execution import (
    CognitionDecodingControl,
    CognitionReasoningMode,
    normalize_cognition_execution_capabilities,
)


def test_normalizes_provider_owned_facts_into_cogp_capability_view() -> None:
    capabilities = normalize_cognition_execution_capabilities(
        structured_output=True,
        streaming=True,
        reasoning_modes=(),
        bounded_reasoning_budget=False,
        decoding_controls=("temperature", "top_p"),
    )

    assert capabilities.structured_output is True
    assert capabilities.streaming is True
    assert capabilities.reasoning_modes == frozenset()
    assert capabilities.bounded_reasoning_budget is False
    assert capabilities.decoding_controls == frozenset(
        {CognitionDecodingControl.TEMPERATURE, CognitionDecodingControl.TOP_P}
    )


def test_normalization_maps_known_reasoning_and_decoding_vocabularies() -> None:
    capabilities = normalize_cognition_execution_capabilities(
        structured_output=True,
        streaming=False,
        reasoning_modes=("bounded", "off"),
        bounded_reasoning_budget=True,
        decoding_controls=("max_output_tokens", "temperature"),
    )

    assert capabilities.reasoning_modes == frozenset(
        {CognitionReasoningMode.OFF, CognitionReasoningMode.BOUNDED}
    )
    assert capabilities.decoding_controls == frozenset(
        {
            CognitionDecodingControl.MAX_OUTPUT_TOKENS,
            CognitionDecodingControl.TEMPERATURE,
        }
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reasoning_modes", ("auto",)),
        ("reasoning_modes", ("mystery",)),
        ("decoding_controls", ("seed",)),
        ("decoding_controls", ("mystery",)),
    ],
)
def test_normalization_fails_closed_on_non_cogp_vocabulary(
    field: str,
    value: tuple[str, ...],
) -> None:
    kwargs = {
        "structured_output": True,
        "streaming": True,
        "reasoning_modes": (),
        "bounded_reasoning_budget": False,
        "decoding_controls": (),
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        normalize_cognition_execution_capabilities(**kwargs)


def test_normalization_rejects_duplicate_provider_facts() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        normalize_cognition_execution_capabilities(
            structured_output=True,
            streaming=True,
            reasoning_modes=(),
            bounded_reasoning_budget=False,
            decoding_controls=("temperature", "temperature"),
        )
