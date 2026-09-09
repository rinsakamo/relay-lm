from __future__ import annotations

import pytest

from relaylm.providers.llama_cpp_reasoning import (
    LlamaCppReasoningCapabilityAttestation,
    LlamaCppReasoningCapabilityError,
    realize_llama_cpp_reasoning_request,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningApplicationStatus,
    OpenAICompatibleReasoningRequest,
)


REQUEST_MODEL = "gemma-local"


def _capability(*, enable_thinking_supported: bool = True) -> LlamaCppReasoningCapabilityAttestation:
    return LlamaCppReasoningCapabilityAttestation(
        request_model=REQUEST_MODEL,
        enable_thinking_supported=enable_thinking_supported,
    )


def test_llama_cpp_reasoning_capability_has_backend_specific_identity() -> None:
    capability = _capability()

    assert capability.to_mapping() == {
        "format_version": 1,
        "backend": "llama_cpp",
        "request_model": REQUEST_MODEL,
        "enable_thinking_supported": True,
        "reasoning_capabilities": {
            "mode_control_supported": True,
            "supported_mode_values": ["off"],
            "mode_values_known": True,
            "token_budget_supported": False,
        },
    }


def test_llama_cpp_realizes_off_as_enable_thinking_false() -> None:
    realization = realize_llama_cpp_reasoning_request(
        request=OpenAICompatibleReasoningRequest(mode="off"),
        capability=_capability(),
    )

    assert realization.application.status is OpenAICompatibleReasoningApplicationStatus.APPLIED
    assert realization.application.requested == (("mode", "off"),)
    assert realization.application.wire_fields == (
        ("chat_template_kwargs.enable_thinking", False),
    )
    assert realization.to_request_fields() == {
        "chat_template_kwargs": {"enable_thinking": False}
    }


def test_llama_cpp_realizer_rejects_off_without_attested_template_control() -> None:
    with pytest.raises(LlamaCppReasoningCapabilityError, match="enable_thinking"):
        realize_llama_cpp_reasoning_request(
            request=OpenAICompatibleReasoningRequest(mode="off"),
            capability=_capability(enable_thinking_supported=False),
        )


def test_llama_cpp_realizer_rejects_bounded_or_token_budget() -> None:
    with pytest.raises(LlamaCppReasoningCapabilityError, match="qualified only"):
        realize_llama_cpp_reasoning_request(
            request=OpenAICompatibleReasoningRequest(mode="bounded", token_budget=16),
            capability=_capability(),
        )


def test_llama_cpp_omitted_reasoning_emits_no_request_fields() -> None:
    realization = realize_llama_cpp_reasoning_request(
        request=OpenAICompatibleReasoningRequest(),
        capability=_capability(),
    )

    assert realization.application.status is OpenAICompatibleReasoningApplicationStatus.OMITTED
    assert realization.to_request_fields() == {}
