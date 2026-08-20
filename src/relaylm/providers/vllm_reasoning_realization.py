from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningApplication,
    OpenAICompatibleReasoningApplicationStatus,
    OpenAICompatibleReasoningRequest,
    ReasoningMapping,
)
from relaylm.providers.vllm_reasoning import VLLMReasoningWireControls
from relaylm.providers.vllm_reasoning_capability import (
    TemplateMapping,
    VLLMReasoningCapabilityAttestation,
    VLLMReasoningCapabilityStatus,
)


class VLLMReasoningRealizationError(ValueError):
    """Fail-closed error before an unattested vLLM reasoning field is sent."""


@dataclass(frozen=True, slots=True)
class VLLMReasoningRealization:
    """Resolved vLLM fields and applied identity from one canonical serializer."""

    request: OpenAICompatibleReasoningRequest
    wire_controls: VLLMReasoningWireControls
    template_kwargs: TemplateMapping
    application: OpenAICompatibleReasoningApplication

    @property
    def resolved_wire_fields(self) -> ReasoningMapping:
        return self.application.wire_fields

    def to_request_fields(self) -> dict[str, object]:
        if self.application.status is OpenAICompatibleReasoningApplicationStatus.OMITTED:
            return {}
        if self.application.status is not OpenAICompatibleReasoningApplicationStatus.APPLIED:
            raise VLLMReasoningRealizationError(
                "vLLM reasoning request is not semantically attested; refusing wire"
            )

        fields: dict[str, object] = self.wire_controls.to_mapping()
        if self.template_kwargs:
            fields["chat_template_kwargs"] = dict(self.template_kwargs)
        return fields

    def to_mapping(self) -> dict[str, object]:
        return {
            "requested": self.request.to_mapping(),
            "resolved": dict(self.resolved_wire_fields),
            "applied": self.application.to_mapping(),
            "request_fields": self.to_request_fields(),
        }


def realize_vllm_reasoning_request(
    *,
    request: OpenAICompatibleReasoningRequest,
    capability: VLLMReasoningCapabilityAttestation,
    existing_chat_template_kwargs: Mapping[str, object] | None = None,
) -> VLLMReasoningRealization:
    """Map one resolved RelayLM request using only attested vLLM capability.

    ``bounded`` never chooses its numeric budget; it carries the explicit value
    already present in ``request``. The exact request fields and applied identity
    are produced by this same function.
    """

    if not isinstance(request, OpenAICompatibleReasoningRequest):
        raise TypeError("request must be OpenAICompatibleReasoningRequest")
    if not isinstance(capability, VLLMReasoningCapabilityAttestation):
        raise TypeError("capability must be VLLMReasoningCapabilityAttestation")
    existing = _validate_existing_template_kwargs(existing_chat_template_kwargs)

    if not request.requested:
        if existing:
            raise VLLMReasoningRealizationError(
                "template kwargs require an explicit vLLM reasoning request"
            )
        return VLLMReasoningRealization(
            request=request,
            wire_controls=VLLMReasoningWireControls(),
            template_kwargs=(),
            application=OpenAICompatibleReasoningApplication(
                status=OpenAICompatibleReasoningApplicationStatus.OMITTED,
                requested=(),
                wire_fields=(),
            ),
        )

    if request.mode is None and request.token_budget is not None:
        raise ValueError("reasoning token budget requires bounded mode")
    if request.mode == "off" and request.token_budget is not None:
        raise ValueError("off reasoning must not carry a token budget")
    if request.mode == "bounded" and request.token_budget is None:
        raise ValueError("bounded reasoning requires an explicit token budget")
    if request.mode not in {"off", "bounded"}:
        return _unsupported_realization(request)

    if request.mode == "off":
        if existing:
            raise VLLMReasoningRealizationError(
                "enable_thinking template kwargs conflict with attested OFF wire"
            )
        if capability.reasoning_off.status is not VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED:
            return _unsupported_realization(request)
        controls = VLLMReasoningWireControls(reasoning_effort="none")
        wire_fields = controls.wire_fields
        template_kwargs: TemplateMapping = ()
    else:
        if existing and existing != {"enable_thinking": True}:
            raise VLLMReasoningRealizationError(
                "bounded vLLM reasoning requires enable_thinking=true without other template kwargs"
            )
        if capability.reasoning_bounded.status is not VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED:
            return _unsupported_realization(request)
        assert request.token_budget is not None
        controls = VLLMReasoningWireControls(
            thinking_token_budget=request.token_budget
        )
        template_kwargs = (("enable_thinking", True),)
        wire_fields = tuple(
            sorted(
                (
                    *controls.wire_fields,
                    ("chat_template_kwargs.enable_thinking", True),
                )
            )
        )

    application = OpenAICompatibleReasoningApplication(
        status=OpenAICompatibleReasoningApplicationStatus.APPLIED,
        requested=request.requested,
        wire_fields=wire_fields,
    )
    return VLLMReasoningRealization(
        request=request,
        wire_controls=controls,
        template_kwargs=template_kwargs,
        application=application,
    )


def _unsupported_realization(
    request: OpenAICompatibleReasoningRequest,
) -> VLLMReasoningRealization:
    return VLLMReasoningRealization(
        request=request,
        wire_controls=VLLMReasoningWireControls(),
        template_kwargs=(),
        application=OpenAICompatibleReasoningApplication(
            status=OpenAICompatibleReasoningApplicationStatus.UNSUPPORTED,
            requested=request.requested,
            wire_fields=(),
        ),
    )


def _validate_existing_template_kwargs(
    values: Mapping[str, object] | None,
) -> dict[str, object]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise TypeError("existing_chat_template_kwargs must be a mapping or None")
    if not all(isinstance(key, str) and key.strip() for key in values):
        raise TypeError("existing_chat_template_kwargs keys must be non-empty strings")
    return dict(values)
