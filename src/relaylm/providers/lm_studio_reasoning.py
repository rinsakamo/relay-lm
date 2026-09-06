from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningApplication,
    OpenAICompatibleReasoningApplicationStatus,
    OpenAICompatibleReasoningCapabilities,
    OpenAICompatibleReasoningRequest,
)

LM_STUDIO_REASONING_CAPABILITY_ATTESTATION_FORMAT_VERSION = 1
LM_STUDIO_REASONING_PUBLIC_OPTIONS = frozenset(
    {"off", "on", "low", "medium", "high"}
)
LM_STUDIO_CHAT_COMPLETIONS_BINARY_REASONING_OPTIONS = frozenset({"off", "on"})


class LMStudioReasoningCapabilityError(ValueError):
    """LM Studio reasoning metadata cannot truthfully attest the configured runtime."""


@dataclass(frozen=True, slots=True)
class LMStudioReasoningCapabilityAttestation:
    """Content-free reasoning capability attested for one loaded LM Studio model.

    The native `/api/v1/models` reasoning object attests public mode options and
    the model/runtime default. It does not, by itself, prove that RelayLM carries
    a per-request override or that an explicit reasoning-token budget is accepted
    for this exact model/runtime.
    """

    request_model: str
    loaded_instance_id: str
    reasoning_exposed: bool
    allowed_options: tuple[str, ...]
    default: str | None
    capabilities: OpenAICompatibleReasoningCapabilities
    format_version: int = LM_STUDIO_REASONING_CAPABILITY_ATTESTATION_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != LM_STUDIO_REASONING_CAPABILITY_ATTESTATION_FORMAT_VERSION:
            raise ValueError(
                "unsupported LM Studio reasoning capability attestation format_version: "
                f"{self.format_version}"
            )
        for name in ("request_model", "loaded_instance_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise TypeError(f"{name} must be a non-empty string")
        if not isinstance(self.reasoning_exposed, bool):
            raise TypeError("reasoning_exposed must be bool")
        if not isinstance(self.allowed_options, tuple):
            raise TypeError("allowed_options must be a tuple")
        if tuple(sorted(self.allowed_options)) != self.allowed_options:
            raise ValueError("allowed_options must be sorted")
        if len(set(self.allowed_options)) != len(self.allowed_options):
            raise ValueError("allowed_options must not contain duplicates")
        if not all(
            isinstance(value, str) and value in LM_STUDIO_REASONING_PUBLIC_OPTIONS
            for value in self.allowed_options
        ):
            raise ValueError("allowed_options contain an unsupported public option")
        if not isinstance(self.capabilities, OpenAICompatibleReasoningCapabilities):
            raise TypeError(
                "capabilities must be OpenAICompatibleReasoningCapabilities"
            )

        if self.reasoning_exposed:
            if not self.allowed_options:
                raise ValueError("exposed reasoning requires allowed_options")
            if not isinstance(self.default, str) or self.default not in self.allowed_options:
                raise ValueError(
                    "exposed reasoning default must be present in allowed_options"
                )
            if not self.capabilities.mode_control_supported:
                raise ValueError("exposed reasoning requires mode capability")
            if self.capabilities.supported_mode_values != self.allowed_options:
                raise ValueError(
                    "reasoning capability options must match attested allowed_options"
                )
        else:
            if self.allowed_options or self.default is not None:
                raise ValueError(
                    "unexposed reasoning must not claim options or a default"
                )
            if self.capabilities.mode_control_supported:
                raise ValueError(
                    "unexposed reasoning must not claim mode-control support"
                )

        if self.capabilities.token_budget_supported:
            raise ValueError(
                "LM Studio native reasoning metadata does not attest token-budget support"
            )

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "backend": "lm_studio",
            "request_model": self.request_model,
            "loaded_instance_id": self.loaded_instance_id,
            "reasoning_exposed": self.reasoning_exposed,
            "allowed_options": list(self.allowed_options),
            "default": self.default,
            "reasoning_capabilities": self.capabilities.to_mapping(),
        }


def attest_lm_studio_reasoning_capabilities(
    *,
    models_response: Mapping[str, object],
    request_model: str,
    loaded_instance_id: str,
) -> LMStudioReasoningCapabilityAttestation:
    """Attest exact public reasoning metadata for one configured loaded model.

    This function consumes LM Studio-native `/api/v1/models` data. It is not part
    of the generic OpenAI-compatible protocol and performs no model-name inference.
    """

    if not isinstance(models_response, Mapping):
        raise TypeError("models_response must be a mapping")
    request_model = _non_empty_string(request_model, "request_model")
    loaded_instance_id = _non_empty_string(
        loaded_instance_id, "loaded_instance_id"
    )

    models = _list(models_response.get("models"), "LM Studio models")
    if not all(isinstance(model, Mapping) for model in models):
        raise LMStudioReasoningCapabilityError(
            "LM Studio models response contains a non-object model"
        )
    matches = [model for model in models if model.get("key") == request_model]
    if len(matches) != 1:
        raise LMStudioReasoningCapabilityError(
            "LM Studio models response must contain exactly one matching request model"
        )
    model = matches[0]

    loaded_instances = _list(
        model.get("loaded_instances"), "LM Studio model loaded_instances"
    )
    if len(loaded_instances) != 1 or not isinstance(loaded_instances[0], Mapping):
        raise LMStudioReasoningCapabilityError(
            "LM Studio model must have exactly one loaded instance for unambiguous attestation"
        )
    loaded_id = loaded_instances[0].get("id")
    if loaded_id != loaded_instance_id:
        raise LMStudioReasoningCapabilityError(
            "LM Studio loaded instance identity does not match the configured runtime"
        )

    raw_capabilities = model.get("capabilities")
    if raw_capabilities is None:
        return _unsupported_attestation(
            request_model=request_model,
            loaded_instance_id=loaded_instance_id,
        )
    capabilities = _mapping(raw_capabilities, "LM Studio model capabilities")
    if "reasoning" not in capabilities:
        return _unsupported_attestation(
            request_model=request_model,
            loaded_instance_id=loaded_instance_id,
        )

    reasoning = _mapping(
        capabilities.get("reasoning"), "LM Studio model reasoning capability"
    )
    if "allowed_options" not in reasoning:
        raise LMStudioReasoningCapabilityError(
            "LM Studio reasoning capability is missing allowed_options"
        )
    if "default" not in reasoning:
        raise LMStudioReasoningCapabilityError(
            "LM Studio reasoning capability is missing default"
        )

    allowed_raw = _list(
        reasoning["allowed_options"], "LM Studio reasoning allowed_options"
    )
    if not allowed_raw:
        raise LMStudioReasoningCapabilityError(
            "LM Studio reasoning allowed_options must not be empty"
        )
    if not all(isinstance(value, str) and value.strip() for value in allowed_raw):
        raise LMStudioReasoningCapabilityError(
            "LM Studio reasoning allowed_options must contain non-empty strings"
        )
    if len(set(allowed_raw)) != len(allowed_raw):
        raise LMStudioReasoningCapabilityError(
            "LM Studio reasoning allowed_options must not contain duplicates"
        )
    unknown = set(allowed_raw) - LM_STUDIO_REASONING_PUBLIC_OPTIONS
    if unknown:
        raise LMStudioReasoningCapabilityError(
            "LM Studio reasoning capability contains unsupported public option: "
            + ", ".join(sorted(unknown))
        )
    allowed_options = tuple(sorted(allowed_raw))

    default = _non_empty_string(reasoning["default"], "LM Studio reasoning default")
    if default not in allowed_options:
        raise LMStudioReasoningCapabilityError(
            "LM Studio reasoning default must be present in allowed_options"
        )

    provider_capabilities = OpenAICompatibleReasoningCapabilities(
        mode_control_supported=True,
        supported_mode_values=allowed_options,
        token_budget_supported=False,
    )
    return LMStudioReasoningCapabilityAttestation(
        request_model=request_model,
        loaded_instance_id=loaded_instance_id,
        reasoning_exposed=True,
        allowed_options=allowed_options,
        default=default,
        capabilities=provider_capabilities,
    )


def realize_lm_studio_reasoning_request(
    *,
    request: OpenAICompatibleReasoningRequest,
    capability: LMStudioReasoningCapabilityAttestation,
) -> OpenAICompatibleReasoningApplication:
    """Serialize an attested LM Studio binary mode onto Chat Completions.

    Current RelayLM support is intentionally narrower than LM Studio's native
    reasoning vocabulary. For the Gemma-4 binary capability class used by the
    release reference path, the exact OpenAI-compatible request field is
    ``reasoning_effort`` and the attested public ``off``/``on`` value is carried
    unchanged. Unsupported modes and token budgets fail before network I/O.
    """

    if not isinstance(request, OpenAICompatibleReasoningRequest):
        raise TypeError("request must be OpenAICompatibleReasoningRequest")
    if not isinstance(capability, LMStudioReasoningCapabilityAttestation):
        raise TypeError("capability must be LMStudioReasoningCapabilityAttestation")

    if not request.requested:
        return OpenAICompatibleReasoningApplication(
            status=OpenAICompatibleReasoningApplicationStatus.OMITTED,
            requested=(),
            wire_fields=(),
        )
    if request.token_budget is not None:
        raise LMStudioReasoningCapabilityError(
            "LM Studio reasoning token budget is not attested for Chat Completions"
        )
    if request.mode is None:
        raise LMStudioReasoningCapabilityError(
            "LM Studio explicit reasoning request must include a mode"
        )
    if not capability.reasoning_exposed or request.mode not in capability.allowed_options:
        raise LMStudioReasoningCapabilityError(
            f"LM Studio reasoning mode is not supported by the loaded model: {request.mode}"
        )
    if request.mode not in LM_STUDIO_CHAT_COMPLETIONS_BINARY_REASONING_OPTIONS:
        raise LMStudioReasoningCapabilityError(
            "LM Studio Chat Completions realization is currently qualified only for "
            "binary reasoning modes off/on"
        )

    return OpenAICompatibleReasoningApplication(
        status=OpenAICompatibleReasoningApplicationStatus.APPLIED,
        requested=request.requested,
        wire_fields=(("reasoning_effort", request.mode),),
    )


def _unsupported_attestation(
    *, request_model: str, loaded_instance_id: str
) -> LMStudioReasoningCapabilityAttestation:
    return LMStudioReasoningCapabilityAttestation(
        request_model=request_model,
        loaded_instance_id=loaded_instance_id,
        reasoning_exposed=False,
        allowed_options=(),
        default=None,
        capabilities=OpenAICompatibleReasoningCapabilities(),
    )


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LMStudioReasoningCapabilityError(f"{name} must be an object")
    return value


def _list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise LMStudioReasoningCapabilityError(f"{name} must be an array")
    return value


def _non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LMStudioReasoningCapabilityError(f"{name} must be a non-empty string")
    return value
