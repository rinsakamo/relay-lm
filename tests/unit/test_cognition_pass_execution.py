from __future__ import annotations

import pytest

from relaylm.cognitive import CognitionExecutionMode
from relaylm.cognition_execution import (
    CognitionDecodingControl,
    CognitionExecutionCapabilities,
    CognitionExecutionCapabilityError,
    CognitionOptionStatus,
    CognitionPassPolicy,
    CognitionPassRequest,
    CognitionPolicyUnresolvedError,
    CognitionReasoningMode,
    CognitionReasoningPolicy,
    require_mode_capabilities,
    resolve_pass_request,
)


def test_pass_policy_keeps_auto_semantics_without_numeric_defaults() -> None:
    policy = CognitionPassPolicy()

    assert policy.reasoning == CognitionReasoningPolicy(
        mode=CognitionReasoningMode.AUTO,
        budget=None,
    )
    assert policy.temperature is None
    assert policy.top_p is None
    assert policy.max_output_tokens is None

    bounded = CognitionPassPolicy(
        reasoning=CognitionReasoningPolicy(
            mode=CognitionReasoningMode.BOUNDED,
            budget=768,
        ),
        temperature=0.0,
        top_p=1.0,
        max_output_tokens=512,
    )
    assert bounded.reasoning.budget == 768


def test_pass_policy_rejects_invalid_reasoning_and_numeric_shapes() -> None:
    with pytest.raises(ValueError, match="reasoning budget requires bounded mode"):
        CognitionReasoningPolicy(mode=CognitionReasoningMode.OFF, budget=1)

    with pytest.raises(ValueError, match="reasoning budget must be positive"):
        CognitionReasoningPolicy(mode=CognitionReasoningMode.BOUNDED, budget=0)

    with pytest.raises(ValueError, match="max_output_tokens must be positive"):
        CognitionPassPolicy(max_output_tokens=0)


def test_effective_pass_request_forbids_unresolved_auto() -> None:
    with pytest.raises(CognitionPolicyUnresolvedError, match="reasoning mode"):
        CognitionPassRequest(reasoning_mode=CognitionReasoningMode.AUTO)

    with pytest.raises(ValueError, match="reasoning budget requires bounded mode"):
        CognitionPassRequest(
            reasoning_mode=CognitionReasoningMode.OFF,
            reasoning_budget=128,
        )


def test_capability_resolution_distinguishes_applied_omitted_and_unsupported() -> None:
    capabilities = CognitionExecutionCapabilities(
        structured_output=True,
        streaming=True,
        reasoning_modes=frozenset({CognitionReasoningMode.OFF}),
        bounded_reasoning_budget=False,
        decoding_controls=frozenset({CognitionDecodingControl.TEMPERATURE}),
    )
    request = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.OFF,
        temperature=0.0,
        top_p=1.0,
    )

    resolution = resolve_pass_request(request=request, capabilities=capabilities)

    assert resolution.reasoning_mode.status is CognitionOptionStatus.APPLIED
    assert resolution.reasoning_budget.status is CognitionOptionStatus.OMITTED
    assert resolution.temperature.status is CognitionOptionStatus.APPLIED
    assert resolution.top_p.status is CognitionOptionStatus.UNSUPPORTED
    assert resolution.max_output_tokens.status is CognitionOptionStatus.OMITTED
    assert resolution.unsupported_fields == ("top_p",)
    assert resolution.to_mapping()["top_p"] == {
        "status": "unsupported",
        "value": 1.0,
    }

    with pytest.raises(CognitionExecutionCapabilityError, match="top_p"):
        resolution.require_supported()


def test_bounded_reasoning_budget_requires_both_mode_and_budget_capability() -> None:
    request = CognitionPassRequest(
        reasoning_mode=CognitionReasoningMode.BOUNDED,
        reasoning_budget=256,
    )
    capabilities = CognitionExecutionCapabilities(
        structured_output=True,
        streaming=False,
        reasoning_modes=frozenset({CognitionReasoningMode.BOUNDED}),
        bounded_reasoning_budget=False,
    )

    resolution = resolve_pass_request(request=request, capabilities=capabilities)

    assert resolution.reasoning_mode.status is CognitionOptionStatus.APPLIED
    assert resolution.reasoning_budget.status is CognitionOptionStatus.UNSUPPORTED
    with pytest.raises(CognitionExecutionCapabilityError, match="reasoning_budget"):
        resolution.require_supported()


def test_mode_capabilities_fail_closed_before_generation() -> None:
    no_structured = CognitionExecutionCapabilities(
        structured_output=False,
        streaming=True,
    )
    with pytest.raises(CognitionExecutionCapabilityError, match="structured_output"):
        require_mode_capabilities(
            mode=CognitionExecutionMode.TWO_PASS,
            capabilities=no_structured,
            streaming=False,
        )

    no_streaming = CognitionExecutionCapabilities(
        structured_output=True,
        streaming=False,
    )
    with pytest.raises(CognitionExecutionCapabilityError, match="streaming"):
        require_mode_capabilities(
            mode=CognitionExecutionMode.SINGLE_PASS,
            capabilities=no_streaming,
            streaming=True,
        )

    with pytest.raises(CognitionPolicyUnresolvedError, match="auto"):
        require_mode_capabilities(
            mode=CognitionExecutionMode.AUTO,
            capabilities=no_streaming,
            streaming=False,
        )
