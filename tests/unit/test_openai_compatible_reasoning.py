from __future__ import annotations

import pytest

from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningApplication,
    OpenAICompatibleReasoningApplicationStatus,
    OpenAICompatibleReasoningCapabilities,
    OpenAICompatibleReasoningPreflightStatus,
    OpenAICompatibleReasoningRequest,
    preflight_openai_compatible_reasoning,
)


def test_reasoning_capabilities_distinguish_unsupported_unknown_and_exact_options() -> None:
    unsupported = OpenAICompatibleReasoningCapabilities()
    unknown_options = OpenAICompatibleReasoningCapabilities(
        mode_control_supported=True,
        supported_mode_values=None,
    )
    exact_options = OpenAICompatibleReasoningCapabilities(
        mode_control_supported=True,
        supported_mode_values=("high", "off"),
        token_budget_supported=True,
    )

    assert unsupported.to_mapping() == {
        "mode_control_supported": False,
        "supported_mode_values": [],
        "mode_values_known": False,
        "token_budget_supported": False,
    }
    assert unknown_options.to_mapping() == {
        "mode_control_supported": True,
        "supported_mode_values": [],
        "mode_values_known": False,
        "token_budget_supported": False,
    }
    assert exact_options.to_mapping() == {
        "mode_control_supported": True,
        "supported_mode_values": ["high", "off"],
        "mode_values_known": True,
        "token_budget_supported": True,
    }


def test_reasoning_request_has_no_hidden_default_and_omitted_is_explicit() -> None:
    request = OpenAICompatibleReasoningRequest()
    preflight = preflight_openai_compatible_reasoning(
        request=request,
        capabilities=OpenAICompatibleReasoningCapabilities(),
    )

    assert request.to_mapping() == {}
    assert preflight.status is OpenAICompatibleReasoningPreflightStatus.OMITTED
    assert preflight.unsupported_controls == ()


def test_unknown_or_unsupported_explicit_reasoning_fails_closed_before_wire() -> None:
    request = OpenAICompatibleReasoningRequest(mode="off", token_budget=256)

    unknown = preflight_openai_compatible_reasoning(
        request=request,
        capabilities=OpenAICompatibleReasoningCapabilities(
            mode_control_supported=True,
            supported_mode_values=None,
            token_budget_supported=True,
        ),
    )
    unsupported = preflight_openai_compatible_reasoning(
        request=request,
        capabilities=OpenAICompatibleReasoningCapabilities(),
    )

    assert unknown.status is OpenAICompatibleReasoningPreflightStatus.UNSUPPORTED
    assert unknown.unsupported_controls == ("mode",)
    assert unsupported.status is OpenAICompatibleReasoningPreflightStatus.UNSUPPORTED
    assert unsupported.unsupported_controls == ("mode", "token_budget")


def test_exact_supported_reasoning_is_ready_but_not_falsely_applied() -> None:
    preflight = preflight_openai_compatible_reasoning(
        request=OpenAICompatibleReasoningRequest(mode="off", token_budget=256),
        capabilities=OpenAICompatibleReasoningCapabilities(
            mode_control_supported=True,
            supported_mode_values=("off",),
            token_budget_supported=True,
        ),
    )

    assert preflight.status is OpenAICompatibleReasoningPreflightStatus.READY
    assert preflight.unsupported_controls == ()

    with pytest.raises(ValueError, match="exact wire fields"):
        OpenAICompatibleReasoningApplication(
            status=OpenAICompatibleReasoningApplicationStatus.APPLIED,
            requested=preflight.requested,
            wire_fields=(),
        )


def test_application_identity_distinguishes_omitted_unsupported_and_applied() -> None:
    omitted = OpenAICompatibleReasoningApplication(
        status=OpenAICompatibleReasoningApplicationStatus.OMITTED,
        requested=(),
        wire_fields=(),
    )
    unsupported = OpenAICompatibleReasoningApplication(
        status=OpenAICompatibleReasoningApplicationStatus.UNSUPPORTED,
        requested=(("mode", "off"),),
        wire_fields=(),
    )
    applied = OpenAICompatibleReasoningApplication(
        status=OpenAICompatibleReasoningApplicationStatus.APPLIED,
        requested=(("mode", "off"),),
        wire_fields=(("reasoning_control", "off"),),
    )

    assert omitted.to_mapping()["status"] == "omitted"
    assert unsupported.to_mapping()["status"] == "unsupported"
    assert applied.to_mapping() == {
        "status": "applied",
        "requested": {"mode": "off"},
        "wire_fields": {"reasoning_control": "off"},
    }
