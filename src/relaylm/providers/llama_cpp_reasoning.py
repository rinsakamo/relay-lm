from __future__ import annotations

from dataclasses import dataclass

from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningApplication,
    OpenAICompatibleReasoningApplicationStatus,
    OpenAICompatibleReasoningCapabilities,
    OpenAICompatibleReasoningPreflightStatus,
    OpenAICompatibleReasoningRequest,
    preflight_openai_compatible_reasoning,
)


LLAMA_CPP_REASONING_ATTESTATION_FORMAT_VERSION = 1


class LlamaCppReasoningCapabilityError(ValueError):
    """Fail-closed error for unattested llama.cpp reasoning carriage."""


@dataclass(frozen=True, slots=True)
class LlamaCppReasoningCapabilityAttestation:
    """Exact llama.cpp request-model capability used for reasoning realization.

    RelayLM currently qualifies provider-neutral OFF through the OpenAI-compatible
    ``reasoning_effort=none`` request field. The exact pinned llama-server maps
    that field to its internal ``enable_thinking=false`` template input. This
    record deliberately does not infer support from the model family name.

    ``enable_thinking_supported`` is retained as the existing constructor field
    for compatibility with the already-merged evaluation host. In this format it
    means that the exact request-model/runtime condition has attested an explicit
    Thinking-OFF control; the qualified public wire emitted by RelayLM is
    ``reasoning_effort=none``.
    """

    request_model: str
    enable_thinking_supported: bool
    format_version: int = LLAMA_CPP_REASONING_ATTESTATION_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != LLAMA_CPP_REASONING_ATTESTATION_FORMAT_VERSION:
            raise ValueError(
                "unsupported llama.cpp reasoning attestation format_version: "
                f"{self.format_version}"
            )
        if not isinstance(self.request_model, str) or not self.request_model.strip():
            raise TypeError("request_model must be a non-empty string")
        if not isinstance(self.enable_thinking_supported, bool):
            raise TypeError("enable_thinking_supported must be bool")

    @property
    def reasoning_effort_none_supported(self) -> bool:
        """Whether explicit OpenAI-compatible OFF is attested for this condition."""

        return self.enable_thinking_supported

    @property
    def capabilities(self) -> OpenAICompatibleReasoningCapabilities:
        return OpenAICompatibleReasoningCapabilities(
            mode_control_supported=self.reasoning_effort_none_supported,
            supported_mode_values=("off",)
            if self.reasoning_effort_none_supported
            else None,
            token_budget_supported=False,
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "backend": "llama_cpp",
            "request_model": self.request_model,
            "enable_thinking_supported": self.enable_thinking_supported,
            "reasoning_effort_none_supported": self.reasoning_effort_none_supported,
            "reasoning_capabilities": self.capabilities.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class LlamaCppReasoningRealization:
    """Resolved llama.cpp request fields plus content-free application identity."""

    request: OpenAICompatibleReasoningRequest
    application: OpenAICompatibleReasoningApplication

    def to_request_fields(self) -> dict[str, object]:
        if self.application.status is OpenAICompatibleReasoningApplicationStatus.OMITTED:
            return {}
        if self.application.status is not OpenAICompatibleReasoningApplicationStatus.APPLIED:
            raise LlamaCppReasoningCapabilityError(
                "llama.cpp reasoning request is not semantically attested; refusing wire"
            )
        return {"reasoning_effort": "none"}

    def to_mapping(self) -> dict[str, object]:
        return {
            "requested": self.request.to_mapping(),
            "applied": self.application.to_mapping(),
            "request_fields": self.to_request_fields(),
        }


def realize_llama_cpp_reasoning_request(
    *,
    request: OpenAICompatibleReasoningRequest,
    capability: LlamaCppReasoningCapabilityAttestation,
) -> LlamaCppReasoningRealization:
    """Map provider-neutral reasoning intent onto an attested llama.cpp wire."""

    if not isinstance(request, OpenAICompatibleReasoningRequest):
        raise TypeError("request must be OpenAICompatibleReasoningRequest")
    if not isinstance(capability, LlamaCppReasoningCapabilityAttestation):
        raise TypeError(
            "capability must be LlamaCppReasoningCapabilityAttestation"
        )

    if not request.requested:
        return LlamaCppReasoningRealization(
            request=request,
            application=OpenAICompatibleReasoningApplication(
                status=OpenAICompatibleReasoningApplicationStatus.OMITTED,
                requested=(),
                wire_fields=(),
            ),
        )

    if request.token_budget is not None or request.mode != "off":
        raise LlamaCppReasoningCapabilityError(
            "current llama.cpp reasoning carriage is qualified only for explicit off "
            "without a token budget"
        )

    preflight = preflight_openai_compatible_reasoning(
        request=request,
        capabilities=capability.capabilities,
    )
    if preflight.status is not OpenAICompatibleReasoningPreflightStatus.READY:
        raise LlamaCppReasoningCapabilityError(
            "llama.cpp reasoning_effort=none is not attested for this request model"
        )

    return LlamaCppReasoningRealization(
        request=request,
        application=OpenAICompatibleReasoningApplication(
            status=OpenAICompatibleReasoningApplicationStatus.APPLIED,
            requested=request.requested,
            wire_fields=(("reasoning_effort", "none"),),
        ),
    )
